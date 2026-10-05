# Mapas no frontend — uma pilha só

A abstração oficial é `src/providers/maps/` (`IMapProvider`, `IMap`, `IPolyline`,
`IMarker`, `IPolygon` + `MapProviderFactory`, que resolve `google | mapbox | osm`
a partir de `/api/config/`). Nenhum componente fala `google.maps`, `mapboxgl` ou
`L.*` diretamente (CLAUDE.md §2.7 e §8; EV-0012).

Blocos reutilizáveis desta pasta:

| Ficheiro | Para quê |
|---|---|
| `MapCanvas.vue` | cria o mapa do provider configurado e emite `ready(map)`; overlays Vue vão no slot |
| `MapPopup.vue` | janela ancorada numa coordenada (substitui `InfoWindow`/popups nativos) |
| `MapControls.vue` | botões «enquadrar» / «legenda» |
| `RadiusSearchTool.vue` | pesquisa por raio — **ainda Google-only**, desligada por omissão (dívida em EV-0012) |

Composables: `src/composables/useRouteDrawing.js` (desenhar/editar um traçado com
vértices arrastáveis), `src/composables/useRealtimeStatus.js` (estado em tempo real),
`src/composables/map/{useMapData,useMapSelection}.js` (dados e seleção do
`CustomMapViewer`).

Exemplo mínimo:

```vue
<MapCanvas :center="{ lat: -16.68, lng: -49.26 }" :zoom="12" @ready="onReady">
  <MapPopup v-if="map && popup" :map="map" :position="popup.position">…</MapPopup>
</MapCanvas>
```

```js
const onReady = (m) => {
  map.value = m;
  const line = m.createPolyline({ path, strokeColor: '#2563eb' });
  line.on('click', (e) => { popup.value = { position: { lat: e.lat, lng: e.lng } }; });
};
```
