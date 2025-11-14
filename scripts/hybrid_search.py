#!/usr/bin/env python3
"""
Recherche hybride : combine recherche sémantique + recherche par mots-clés
"""

import asyncio
import re
from typing import List, Dict, Any, Set
from collections import Counter
import math
from rich.console import Console

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.chroma_db import create_chroma_db
from ingestion.embedder import create_embedder

console = Console()

class HybridSearchEngine:
    """Moteur de recherche hybride combinant sémantique + mots-clés"""
    
    def __init__(self):
        self.db = create_chroma_db()
        self.embedder = create_embedder()
        
        # Mots vides français
        self.stop_words = {
            'le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir', 'que', 'pour',
            'dans', 'ce', 'son', 'une', 'sur', 'avec', 'ne', 'se', 'pas', 'tout', 'plus',
            'par', 'grand', 'en', 'une', 'être', 'et', 'à', 'il', 'avoir', 'ne', 'je', 'son',
            'que', 'se', 'qui', 'ce', 'dans', 'en', 'du', 'elle', 'au', 'de', 'ce', 'le',
            'pour', 'sont', 'avec', 'ils', 'nous', 'tout', 'votre', 'ou', 'sur', 'faire',
            'ses', 'était', 'vous', 'lui', 'ma', 'je', 'leur', 'y', 'ces', 'si', 'cette',
            'mais', 'ou', 'très', 'comme', 'alors', 'sans', 'bien', 'où', 'quoi', 'comment',
            'quand', 'pourquoi', 'est', 'sont', 'était', 'étaient', 'sera', 'seront'
        }
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extrait les mots-clés d'un texte"""
        # Nettoie le texte
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Divise en mots
        words = text.split()
        
        # Filtre les mots vides et courts
        keywords = [
            word for word in words 
            if len(word) > 2 and word not in self.stop_words
        ]
        
        return keywords
    
    def calculate_bm25_score(self, query_keywords: List[str], doc_text: str, 
                           corpus_stats: Dict[str, Any]) -> float:
        """Calcule le score BM25 pour un document"""
        doc_keywords = self.extract_keywords(doc_text)
        doc_length = len(doc_keywords)
        
        if doc_length == 0:
            return 0.0
        
        # Paramètres BM25
        k1 = 1.5
        b = 0.75
        
        avg_doc_length = corpus_stats.get('avg_doc_length', 100)
        total_docs = corpus_stats.get('total_docs', 1)
        
        score = 0.0
        doc_word_counts = Counter(doc_keywords)
        
        for keyword in query_keywords:
            if keyword in doc_word_counts:
                tf = doc_word_counts[keyword]
                
                # Document frequency (approximation)
                df = corpus_stats.get('word_frequencies', {}).get(keyword, 1)
                idf = math.log((total_docs - df + 0.5) / (df + 0.5))
                
                # BM25 formula
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))
                
                score += idf * (numerator / denominator)
        
        return score
    
    async def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche sémantique classique"""
        try:
            results = await self.db.search_chunks_by_text(query, limit=limit)
            
            # Ajoute le type de recherche
            for result in results:
                result['search_type'] = 'semantic'
            
            return results
            
        except Exception as e:
            console.print(f"[red]Erreur recherche sémantique: {e}[/red]")
            return []
    
    async def keyword_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche par mots-clés avec BM25"""
        try:
            # Extrait les mots-clés de la requête
            query_keywords = self.extract_keywords(query)
            
            if not query_keywords:
                return []
            
            # Récupère tous les documents (pour une vraie implémentation, 
            # on utiliserait un index inversé)
            all_results = await self.db.search_chunks_by_text("", limit=1000)
            
            # Statistiques du corpus (approximation)
            corpus_stats = {
                'total_docs': len(all_results),
                'avg_doc_length': 100,  # Approximation
                'word_frequencies': {}  # Approximation
            }
            
            # Calcule les scores BM25
            scored_results = []
            for result in all_results:
                bm25_score = self.calculate_bm25_score(
                    query_keywords, 
                    result['content'], 
                    corpus_stats
                )
                
                if bm25_score > 0:
                    result['similarity'] = bm25_score
                    result['search_type'] = 'keyword'
                    scored_results.append(result)
            
            # Trie par score et limite
            scored_results.sort(key=lambda x: x['similarity'], reverse=True)
            return scored_results[:limit]
            
        except Exception as e:
            console.print(f"[red]Erreur recherche mots-clés: {e}[/red]")
            return []
    
    def combine_results(self, semantic_results: List[Dict[str, Any]], 
                       keyword_results: List[Dict[str, Any]],
                       semantic_weight: float = 0.7) -> List[Dict[str, Any]]:
        """Combine les résultats sémantiques et par mots-clés"""
        
        # Normalise les scores sémantiques (0-1)
        if semantic_results:
            max_sem_score = max(r['similarity'] for r in semantic_results)
            min_sem_score = min(r['similarity'] for r in semantic_results)
            sem_range = max_sem_score - min_sem_score
            
            if sem_range > 0:
                for result in semantic_results:
                    result['normalized_similarity'] = (
                        (result['similarity'] - min_sem_score) / sem_range
                    )
            else:
                for result in semantic_results:
                    result['normalized_similarity'] = 1.0
        
        # Normalise les scores BM25 (0-1)
        if keyword_results:
            max_kw_score = max(r['similarity'] for r in keyword_results)
            min_kw_score = min(r['similarity'] for r in keyword_results)
            kw_range = max_kw_score - min_kw_score
            
            if kw_range > 0:
                for result in keyword_results:
                    result['normalized_similarity'] = (
                        (result['similarity'] - min_kw_score) / kw_range
                    )
            else:
                for result in keyword_results:
                    result['normalized_similarity'] = 1.0
        
        # Combine les résultats
        combined = {}
        
        # Ajoute les résultats sémantiques
        for result in semantic_results:
            doc_id = result['id']
            combined[doc_id] = {
                **result,
                'combined_score': result['normalized_similarity'] * semantic_weight,
                'semantic_score': result['normalized_similarity'],
                'keyword_score': 0.0
            }
        
        # Ajoute/combine les résultats par mots-clés
        keyword_weight = 1.0 - semantic_weight
        for result in keyword_results:
            doc_id = result['id']
            
            if doc_id in combined:
                # Document déjà trouvé par recherche sémantique
                combined[doc_id]['keyword_score'] = result['normalized_similarity']
                combined[doc_id]['combined_score'] += (
                    result['normalized_similarity'] * keyword_weight
                )
                combined[doc_id]['search_type'] = 'hybrid'
            else:
                # Nouveau document trouvé uniquement par mots-clés
                combined[doc_id] = {
                    **result,
                    'combined_score': result['normalized_similarity'] * keyword_weight,
                    'semantic_score': 0.0,
                    'keyword_score': result['normalized_similarity'],
                    'search_type': 'keyword'
                }
        
        # Convertit en liste et trie par score combiné
        final_results = list(combined.values())
        final_results.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return final_results
    
    async def hybrid_search(self, query: str, limit: int = 5, 
                          semantic_weight: float = 0.7) -> List[Dict[str, Any]]:
        """
        Recherche hybride combinant sémantique et mots-clés
        
        Args:
            query: Requête de recherche
            limit: Nombre maximum de résultats
            semantic_weight: Poids de la recherche sémantique (0-1)
            
        Returns:
            Liste des résultats combinés
        """
        console.print(f"[cyan]🔍 Recherche hybride: '{query}'[/cyan]")
        
        # Lance les deux types de recherche en parallèle
        semantic_task = self.semantic_search(query, limit * 2)
        keyword_task = self.keyword_search(query, limit * 2)
        
        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task
        )
        
        console.print(f"[dim]Sémantique: {len(semantic_results)} résultats[/dim]")
        console.print(f"[dim]Mots-clés: {len(keyword_results)} résultats[/dim]")
        
        # Combine les résultats
        combined_results = self.combine_results(
            semantic_results, keyword_results, semantic_weight
        )
        
        # Limite le nombre de résultats finaux
        final_results = combined_results[:limit]
        
        console.print(f"[green]✓ {len(final_results)} résultats combinés[/green]")
        
        return final_results
    
    async def close(self):
        """Ferme les connexions"""
        await self.db.close()


# Test de la recherche hybride
async def test_hybrid_search():
    """Teste la recherche hybride"""
    console.print("[bold blue]🧪 TEST DE LA RECHERCHE HYBRIDE[/bold blue]")
    console.print()
    
    search_engine = HybridSearchEngine()
    
    test_queries = [
        "ESP32 microcontrôleur caractéristiques",
        "machine learning algorithmes",
        "JavaScript développement web",
        "réseaux neurones apprentissage"
    ]
    
    try:
        for query in test_queries:
            console.print(f"[yellow]Query: {query}[/yellow]")
            
            # Recherche hybride
            results = await search_engine.hybrid_search(query, limit=3)
            
            for i, result in enumerate(results, 1):
                console.print(f"  {i}. [{result['search_type']}] {result['content'][:100]}...")
                console.print(f"     Score: {result['combined_score']:.3f} "
                            f"(sem: {result['semantic_score']:.3f}, "
                            f"kw: {result['keyword_score']:.3f})")
            
            console.print()
    
    finally:
        await search_engine.close()


if __name__ == "__main__":
    asyncio.run(test_hybrid_search())