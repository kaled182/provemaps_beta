console.log("=== VALIDAÇÃO MANUAL: Elementos de Vídeo no Modal ===\n");

// Aguardar 2 segundos para garantir que modal está aberto
setTimeout(() => {
    console.log("1. Procurando elementos <video> no DOM...");
    
    const allVideos = document.querySelectorAll('video');
    const mosaicVideos = document.querySelectorAll('.mosaic-video, [class*="mosaic"] video, [class*="camera"] video');
    
    console.log(`\n📊 RESULTADOS:`);
    console.log(`   Total de <video> no DOM: ${allVideos.length}`);
    console.log(`   Vídeos de mosaico específicos: ${mosaicVideos.length}`);
    
    if (allVideos.length === 0) {
        console.error("\n❌ FALHA: Nenhum elemento <video> encontrado!");
        console.log("\n🔍 Possíveis causas:");
        console.log("   1. Modal de mosaico não está aberto");
        console.log("   2. v-if/v-show impedindo renderização");
        console.log("   3. mosaicCameras.value está vazio");
        console.log("\n💡 Solução: Abra o modal de câmeras manualmente e execute este script novamente");
    } else {
        console.log("\n✅ SUCESSO: Elementos <video> encontrados!");
        
        console.log("\n📹 Análise detalhada dos vídeos:");
        allVideos.forEach((video, index) => {
            const hasSrcObject = video.srcObject !== null;
            const isPlaying = !video.paused;
            const dimensions = `${video.videoWidth}x${video.videoHeight}`;
            const classes = video.className || '(sem classe)';
            const parent = video.parentElement?.className || '(sem parent)';
            
            console.log(`\n   Vídeo ${index + 1}:`);
            console.log(`      ID: ${video.id || '(sem ID)'}`);
            console.log(`      Classes: ${classes}`);
            console.log(`      Parent: ${parent}`);
            console.log(`      srcObject: ${hasSrcObject ? '✓ Presente' : '✗ null'}`);
            console.log(`      Reproduzindo: ${isPlaying ? '✓ Sim' : '✗ Não'}`);
            console.log(`      Dimensões: ${dimensions === '0x0' ? 'Ainda carregando' : dimensions}`);
            console.log(`      Autoplay: ${video.autoplay}`);
            console.log(`      Muted: ${video.muted}`);
            
            if (hasSrcObject) {
                const tracks = video.srcObject.getTracks();
                console.log(`      Tracks no stream: ${tracks.length}`);
                tracks.forEach(track => {
                    console.log(`         - ${track.kind}: ${track.label} (${track.readyState})`);
                });
            }
        });
        
        console.log("\n🎯 Resumo:");
        const withStream = Array.from(allVideos).filter(v => v.srcObject !== null).length;
        const playing = Array.from(allVideos).filter(v => !v.paused).length;
        
        console.log(`   Vídeos com stream: ${withStream}/${allVideos.length}`);
        console.log(`   Vídeos reproduzindo: ${playing}/${allVideos.length}`);
        
        if (withStream === 0) {
            console.warn("\n⚠️ ATENÇÃO: Elementos <video> existem mas nenhum tem srcObject!");
            console.log("   Isso indica que:");
            console.log("   1. Conexões WebRTC não foram estabelecidas");
            console.log("   2. useWebRTC não está atribuindo streams");
            console.log("   3. Verifique logs do console para erros de WebRTC");
        } else if (playing < withStream) {
            console.warn("\n⚠️ ATENÇÃO: Alguns vídeos têm stream mas não estão reproduzindo!");
            console.log("   Verifique se autoplay está funcionando corretamente");
        } else {
            console.log("\n🎉 TUDO OK: Vídeos renderizados e reproduzindo!");
        }
    }
    
    // Verificar refs do Vue
    console.log("\n\n🔧 Verificando refs do Vue...");
    const app = document.querySelector('#app').__vue_app__;
    if (app) {
        console.log("✓ Vue app encontrado");
        console.log("  Versão Vue:", app.version);
    } else {
        console.log("✗ Vue app não encontrado");
    }
    
}, 2000);

console.log("\n⏳ Aguardando 2 segundos...");
console.log("💡 INSTRUÇÕES:");
console.log("   1. Abra o modal de mosaico de câmeras");
console.log("   2. Cole este script no console");
console.log("   3. Aguarde os resultados");
