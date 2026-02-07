#!/usr/bin/env python3
"""
Teste automatizado: Validação de renderização de vídeos
Usa pytest + Playwright para validar que os elementos <video> existem no DOM
"""

import os
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠ Playwright não instalado. Instale com: pip install playwright")
    print("  Depois execute: playwright install chromium")

# URL base configur ável (Docker ou local)
BASE_URL = os.getenv('TEST_BASE_URL', 'http://localhost:8000')

def test_mosaic_modal_rendering():
    """
    Teste E2E: Valida que o modal de mosaico renderiza elementos <video>
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("\n❌ SKIP: Playwright não disponível")
        return False
    
    print("\n=== TESTE: Renderização de Vídeos no Modal ===\n")
    
    with sync_playwright() as p:
        # Configurar browser
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        # Configurar console listener
        console_logs = []
        def handle_console(msg):
            if '[SiteDetailsModal]' in msg.text:
                console_logs.append(msg.text)
                print(f"  [Console] {msg.text}")
        
        page.on('console', handle_console)
        
        try:
            # 1. Navegar para dashboard
            print(f"1. Navegando para {BASE_URL}...")
            page.goto(f'{BASE_URL}/monitoring/backbone/map/default', timeout=10000)
            time.sleep(5)  # Aguardar mapa carregar
            
            # 2. Procurar qualquer marcador de site no mapa
            print("2. Procurando sites no mapa...")
            
            # Tentar diferentes seletores
            site_markers = page.locator('.leaflet-marker-icon, [class*="marker"]').all()
            
            if len(site_markers) == 0:
                print("✗ FAIL: Nenhum marcador de site encontrado no mapa")
                print("  Verifique se o mapa está carregando corretamente")
                screenshot_path = Path(__file__).parent / 'test-screenshot-no-markers.png'
                page.screenshot(path=str(screenshot_path))
                print(f"  Screenshot salvo: {screenshot_path}")
                browser.close()
                return False
            
            print(f"✓ Encontrados {len(site_markers)} marcadores no mapa")
            
            # Clicar no primeiro marcador
            print("3. Clicando no primeiro marcador...")
            site_markers[0].click()
            time.sleep(2)
            
            # 4. Verificar se modal abriu
            print("4. Verificando se modal do site abriu...")
            modal = page.locator('.modal-overlay, [class*="modal"], .site-details').first
            if not modal.is_visible(timeout=5000):
                print("✗ FAIL: Modal do site não abriu")
                screenshot_path = Path(__file__).parent / 'test-screenshot-no-modal.png'
                page.screenshot(path=str(screenshot_path))
                print(f"  Screenshot salvo: {screenshot_path}")
                browser.close()
                return False
            
            print("✓ Modal do site aberto")
            
            # 5. Procurar botao/card de cameras
            print("5. Procurando botao de cameras...")
            
            # Tentar diferentes seletores para o botao de cameras
            camera_selectors = [
                'text=Cameras',
                'text=Camera',
                'text=Mosaico',
                '[class*="camera"]',
                'button:has-text("Cameras")',
                'button:has-text("Camera")'
            ]
            
            camera_button = None
            for selector in camera_selectors:
                try:
                    btn = page.locator(selector).first
              7. Verificar elementos <video> no DOM
            print("7    camera_button = btn
                        print(f"  ✓ Encontrado com seletor: {selector}")
                        break
                except:
                    continue
            
            if not camera_button:
                print("X FAIL: Botao de cameras nao encontrado")
                print("  Possiveis causas:")
                print("  - Site nao possui cameras cadastradas")
                print("  - Modal tem estrutura diferente")
                screenshot_path = Path(__file__).parent / 'test-screenshot-no-camera-btn.png'
                page.screenshot(path=str(screenshot_path))
                print(f"  Screenshot salvo: {screenshot_path}")
                browser.close()
                return False
            
            # 6. Clicar no botao de cameras
            print("6. Abrindo modal de mosaico...")
            camera_button.click()
            time.sleep(3)  # Aguardar abertura do mosaico
            
            # 7. Verificar elementos <video> no DOM
            print("7. Verificando elementos <video> no DOM...")
            
            # Aguardar um pouco mais para renderizacao
            time.sleep(2)
            
            # Buscar todos os videos
            all_videos = page.locator('video').all()
            mosaic_videos = page.locator('.mosaic-video, [class*="mosaic"] video').all()
            
            print(f"\n=== RESULTADOS ===")
            print(f"Total de <video> no DOM: {len(all_videos)}")
            print(f"Vídeos de mosaico: {len(mosaic_videos)}")
            
            # Analisar console logs
            print(f"\n=== LOGS DO CONSOLE ({len(console_logs)}) ===")
            for log in console_logs[-10:]:  # Últimos 10 logs
                print(f"  {log}")
            
            # Validações
            if len(all_videos) == 0:
                print("\n✗ FAIL: Nenhum elemento <video> encontrado no DOM!")
                print("\nPossíveis causas:")
                print("  1. Modal de mosaico não está visível (v-if/v-show)")
                print("  2. Vue não renderizou os componentes")
                print("  3. mosaicCameras.value está vazio")
                
                # Screenshot para debug
                screenshot_path = Path(__file__).parent / 'test-screenshot-fail.png'
                page.screenshot(path=str(screenshot_path))
                print(f"\nScreenshot salvo em: {screenshot_path}")
                
                browser.close()
                return False
            
            # Verificar atributos dos vídeos
            print("\n=== ANÁLISE DOS VÍDEOS ===")
            for i, video in enumerate(mosaic_videos[:4]):  # Primeiros 4
                src_object = video.evaluate('el => el.srcObject')
                autoplay = video.get_attribute('autoplay')
                muted = video.get_attribute('muted')
                
                print(f"\nVídeo {i+1}:")
                print(f"  srcObject: {'✓ Presente' if src_object else '✗ null'}")
                print(f"  autoplay: {autoplay}")
                print(f"  muted: {muted}")
            
            # Screenshot de sucesso
            screenshot_path = Path(__file__).parent / 'test-screenshot-success.png'
            page.screenshot(path=str(screenshot_path))
            print(f"\nScreenshot salvo em: {screenshot_path}")
            
            print("\n✓ PASS: Elementos <video> encontrados no DOM")
            
            # Manter browser aberto para inspeção manual
            print("\nBrowser ficará aberto por 10s para inspeção manual...")
            time.sleep(10)
            
            browser.close()
            return True
            
        except Exception as e:
            print(f"\n✗ ERRO: {e}")
            screenshot_path = Path(__file__).parent / 'test-screenshot-error.png'
            page.screenshot(path=str(screenshot_path))
            print(f"Screenshot salvo em: {screenshot_path}")
            browser.close()
            return False

if __name__ == '__main__':
    success = test_mosaic_modal_rendering()
    sys.exit(0 if success else 1)
