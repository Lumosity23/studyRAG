/**
 * Demo data for StudyRAG application
 * Used for testing and development
 */

window.DEMO_DATA = {
    // Sample conversations for testing
    conversations: [
        {
            id: "conv_1",
            title: "Analyse de documents PDF",
            last_message: "Pouvez-vous analyser ce document sur l'IA ?",
            updated_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 minutes ago
            message_count: 5,
            status: "active"
        },
        {
            id: "conv_2",
            title: "Recherche sémantique",
            last_message: "Comment fonctionne la recherche vectorielle ?",
            updated_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), // 2 hours ago
            message_count: 12,
            status: "active"
        },
        {
            id: "conv_3",
            title: "Résumé de cours",
            last_message: "Merci pour ce résumé détaillé !",
            updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), // 1 day ago
            message_count: 8,
            status: "active"
        }
    ],

    // Sample messages for testing
    messages: {
        "conv_1": [
            {
                role: "user",
                content: "Bonjour, pouvez-vous analyser ce document PDF sur l'intelligence artificielle ?",
                timestamp: new Date(Date.now() - 1000 * 60 * 25).toISOString()
            },
            {
                role: "assistant",
                content: "Bonjour ! Je serais ravi de vous aider à analyser votre document sur l'intelligence artificielle. J'ai accès à vos documents uploadés et je peux effectuer une analyse approfondie du contenu.\n\nBasé sur les documents que j'ai analysés, voici ce que je peux vous dire :\n\n**Points clés identifiés :**\n- Définitions et concepts fondamentaux de l'IA\n- Applications pratiques dans différents domaines\n- Défis éthiques et techniques\n- Perspectives d'avenir\n\nSouhaitez-vous que je me concentre sur un aspect particulier du document ?",
                timestamp: new Date(Date.now() - 1000 * 60 * 24).toISOString(),
                sources: [
                    {
                        document_title: "Introduction_IA_2024.pdf",
                        similarity_score: 0.92,
                        chunk_index: 1
                    },
                    {
                        document_title: "Applications_IA_Pratiques.pdf",
                        similarity_score: 0.87,
                        chunk_index: 3
                    }
                ]
            },
            {
                role: "user",
                content: "Pouvez-vous me donner plus de détails sur les applications pratiques mentionnées ?",
                timestamp: new Date(Date.now() - 1000 * 60 * 20).toISOString()
            },
            {
                role: "assistant",
                content: "Excellente question ! Voici un aperçu détaillé des applications pratiques de l'IA mentionnées dans vos documents :\n\n## 🏥 **Santé et Médecine**\n- Diagnostic médical assisté par IA\n- Analyse d'imagerie médicale (radiologie, IRM)\n- Découverte de médicaments accélérée\n- Personnalisation des traitements\n\n## 🚗 **Transport et Mobilité**\n- Véhicules autonomes\n- Optimisation du trafic urbain\n- Maintenance prédictive des infrastructures\n\n## 💼 **Entreprise et Finance**\n- Détection de fraudes en temps réel\n- Trading algorithmique\n- Analyse prédictive des marchés\n- Automatisation des processus métier\n\n## 🎓 **Éducation**\n- Systèmes de tutorat intelligent\n- Personnalisation de l'apprentissage\n- Évaluation automatisée\n\nChaque domaine présente des défis spécifiques mais aussi des opportunités considérables. Y a-t-il un secteur qui vous intéresse particulièrement ?",
                timestamp: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
                sources: [
                    {
                        document_title: "Applications_IA_Pratiques.pdf",
                        similarity_score: 0.94,
                        chunk_index: 5
                    },
                    {
                        document_title: "IA_Secteurs_Economiques.pdf",
                        similarity_score: 0.89,
                        chunk_index: 2
                    }
                ]
            }
        ]
    },

    // Sample search results
    searchResults: [
        {
            document_title: "Introduction_IA_2024.pdf",
            content: "L'intelligence artificielle (IA) est une technologie qui permet aux machines d'apprendre, de raisonner et de prendre des décisions de manière autonome. Elle englobe plusieurs sous-domaines comme l'apprentissage automatique, le traitement du langage naturel, et la vision par ordinateur.",
            similarity_score: 0.95,
            chunk_index: 1
        },
        {
            document_title: "Machine_Learning_Basics.pdf",
            content: "L'apprentissage automatique est une branche de l'IA qui permet aux systèmes d'apprendre automatiquement à partir de données sans être explicitement programmés. Il existe trois types principaux : supervisé, non supervisé, et par renforcement.",
            similarity_score: 0.88,
            chunk_index: 3
        },
        {
            document_title: "Deep_Learning_Guide.pdf",
            content: "Les réseaux de neurones profonds sont inspirés du fonctionnement du cerveau humain. Ils sont particulièrement efficaces pour la reconnaissance d'images, le traitement du langage naturel et la génération de contenu.",
            similarity_score: 0.82,
            chunk_index: 7
        }
    ],

    // Sample upload progress states
    uploadStates: {
        pending: {
            status: "pending",
            progress: 0.0,
            message: "En attente de traitement..."
        },
        processing: {
            status: "processing",
            progress: 0.45,
            message: "Extraction du contenu en cours..."
        },
        embedding: {
            status: "processing",
            progress: 0.75,
            message: "Génération des embeddings..."
        },
        completed: {
            status: "completed",
            progress: 1.0,
            message: "Traitement terminé avec succès",
            chunk_count: 24
        },
        failed: {
            status: "failed",
            progress: 0.0,
            message: "Erreur lors du traitement",
            error: "Format de fichier non supporté"
        }
    },

    // Sample API responses for testing
    apiResponses: {
        chatMessage: {
            message: {
                role: "assistant",
                content: "Voici ma réponse basée sur vos documents...",
                timestamp: new Date().toISOString()
            },
            conversation: {
                id: "conv_test",
                title: "Test Conversation",
                updated_at: new Date().toISOString()
            },
            sources_used: [
                {
                    document_title: "Test_Document.pdf",
                    similarity_score: 0.91,
                    chunk_index: 2
                }
            ],
            generation_stats: {
                total_time: 1.23,
                tokens_generated: 150
            }
        },

        searchResponse: {
            results: [
                {
                    document_title: "Sample_Document.pdf",
                    content: "Contenu d'exemple pour la recherche...",
                    similarity_score: 0.89,
                    chunk_index: 1
                }
            ],
            search_time: 0.045,
            total_results: 1
        },

        uploadResponse: {
            document_id: "doc_123456",
            filename: "test_document.pdf",
            processing_status: "pending",
            message: "Document uploadé avec succès. Traitement en cours..."
        }
    },

    // Configuration for demo mode
    config: {
        enableDemoMode: false, // Set to true to use demo data instead of real API
        simulateNetworkDelay: true,
        networkDelayMs: 800,
        enableWebSocketSimulation: false
    }
};

/**
 * Demo mode utilities
 */
window.DemoUtils = {
    // Simulate network delay
    delay: (ms = window.DEMO_DATA.config.networkDelayMs) => {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    // Get random demo response
    getRandomResponse: (responses) => {
        const keys = Object.keys(responses);
        const randomKey = keys[Math.floor(Math.random() * keys.length)];
        return responses[randomKey];
    },

    // Simulate typing delay for streaming responses
    simulateTyping: async function* (text, delayMs = 50) {
        const words = text.split(' ');
        let current = '';

        for (const word of words) {
            current += (current ? ' ' : '') + word;
            yield current;
            await this.delay(delayMs);
        }
    },

    // Generate realistic timestamps
    generateTimestamp: (minutesAgo = 0) => {
        return new Date(Date.now() - minutesAgo * 60 * 1000).toISOString();
    },

    // Simulate file upload progress
    simulateUploadProgress: async function* (filename) {
        const states = [
            { progress: 0.1, message: "Téléchargement..." },
            { progress: 0.3, message: "Validation du fichier..." },
            { progress: 0.5, message: "Extraction du contenu..." },
            { progress: 0.7, message: "Génération des embeddings..." },
            { progress: 0.9, message: "Finalisation..." },
            { progress: 1.0, message: "Traitement terminé ✅" }
        ];

        for (const state of states) {
            yield {
                ...state,
                filename,
                status: state.progress === 1.0 ? "completed" : "processing"
            };
            await this.delay(1000);
        }
    }
};

// Export for use in main application
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DEMO_DATA: window.DEMO_DATA, DemoUtils: window.DemoUtils };
}