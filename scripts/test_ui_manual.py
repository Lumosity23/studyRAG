#!/usr/bin/env python3
"""
Script de test manuel pour l'interface utilisateur StudyRAG
Utilise Selenium pour automatiser les tests de l'UI
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def setup_driver():
    """Configure le driver Chrome pour les tests"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enlever pour voir le navigateur
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Erreur lors de l'initialisation du driver: {e}")
        print("Assurez-vous que ChromeDriver est installé")
        return None

def test_homepage(driver):
    """Test de la page d'accueil"""
    print("🏠 Test de la page d'accueil...")
    
    driver.get("http://localhost:8000")
    
    # Vérifier le titre
    assert "StudyRAG" in driver.title
    print("✅ Titre de la page correct")
    
    # Vérifier la présence des éléments principaux
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "welcome-title"))
        )
        print("✅ Page d'accueil chargée")
    except:
        print("❌ Erreur lors du chargement de la page d'accueil")
        return False
    
    return True

def test_navigation(driver):
    """Test de la navigation"""
    print("🧭 Test de la navigation...")
    
    # Test navigation vers Documents
    try:
        documents_link = driver.find_element(By.CSS_SELECTOR, '[data-route="documents"]')
        documents_link.click()
        time.sleep(2)
        
        # Vérifier que nous sommes sur la page Documents
        page_title = driver.find_element(By.TAG_NAME, "h1")
        assert "Document Management" in page_title.text
        print("✅ Navigation vers Documents fonctionne")
    except Exception as e:
        print(f"❌ Erreur navigation Documents: {e}")
        return False
    
    # Test navigation vers Search
    try:
        search_link = driver.find_element(By.CSS_SELECTOR, '[data-route="search"]')
        search_link.click()
        time.sleep(2)
        
        page_title = driver.find_element(By.TAG_NAME, "h1")
        assert "Search Documents" in page_title.text
        print("✅ Navigation vers Search fonctionne")
    except Exception as e:
        print(f"❌ Erreur navigation Search: {e}")
        return False
    
    return True

def test_upload_interface(driver):
    """Test de l'interface d'upload"""
    print("📤 Test de l'interface d'upload...")
    
    # Aller à la page Documents
    driver.get("http://localhost:8000#documents")
    time.sleep(3)
    
    try:
        # Vérifier la présence de la zone d'upload
        upload_area = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "file-upload"))
        )
        print("✅ Zone d'upload présente")
        
        # Vérifier le texte d'instruction
        upload_text = driver.find_element(By.CLASS_NAME, "file-upload-text")
        assert "Drop files here" in upload_text.text
        print("✅ Instructions d'upload affichées")
        
        return True
    except Exception as e:
        print(f"❌ Erreur interface upload: {e}")
        return False

def test_responsive_design(driver):
    """Test du design responsive"""
    print("📱 Test du design responsive...")
    
    # Test différentes tailles d'écran
    sizes = [
        (1920, 1080),  # Desktop
        (768, 1024),   # Tablet
        (375, 667)     # Mobile
    ]
    
    for width, height in sizes:
        driver.set_window_size(width, height)
        time.sleep(1)
        
        # Vérifier que la page est toujours utilisable
        try:
            driver.find_element(By.CLASS_NAME, "app-container")
            print(f"✅ Design responsive OK pour {width}x{height}")
        except:
            print(f"❌ Problème responsive pour {width}x{height}")
            return False
    
    return True

def test_accessibility(driver):
    """Test basique d'accessibilité"""
    print("♿ Test d'accessibilité...")
    
    driver.get("http://localhost:8000")
    
    try:
        # Vérifier la présence d'un skip link
        skip_link = driver.find_element(By.CLASS_NAME, "skip-link")
        print("✅ Skip link présent")
        
        # Vérifier les attributs ARIA
        nav = driver.find_element(By.TAG_NAME, "nav")
        assert nav.get_attribute("role") == "navigation"
        print("✅ Attributs ARIA présents")
        
        return True
    except Exception as e:
        print(f"❌ Erreur accessibilité: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🚀 Démarrage des tests UI pour StudyRAG")
    print("=" * 50)
    
    # Vérifier que le serveur est démarré
    print("⚠️  Assurez-vous que le serveur FastAPI est démarré sur http://localhost:8000")
    input("Appuyez sur Entrée pour continuer...")
    
    driver = setup_driver()
    if not driver:
        return
    
    try:
        tests = [
            test_homepage,
            test_navigation,
            test_upload_interface,
            test_responsive_design,
            test_accessibility
        ]
        
        results = []
        for test in tests:
            result = test(driver)
            results.append(result)
            time.sleep(1)
        
        print("\n" + "=" * 50)
        print("📊 Résultats des tests:")
        print(f"✅ Tests réussis: {sum(results)}/{len(results)}")
        
        if all(results):
            print("🎉 Tous les tests UI sont passés avec succès!")
        else:
            print("⚠️  Certains tests ont échoué. Vérifiez les détails ci-dessus.")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()