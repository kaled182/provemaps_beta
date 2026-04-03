# Hierarquia de Z-Index dos Modais

## Sistema de Camadas

Para garantir que os modais sempre abram por cima uns dos outros, use a seguinte hierarquia:

### Camadas Base (0-9999)
- **0-999**: Elementos normais da página
- **1000-9999**: Componentes flutuantes (tooltips, dropdowns)

### Camadas de Modais (10000+)
- **10000**: SiteDetailsModal (modal base de sites)
- **11000**: DeviceDetailsModal (modal base de dispositivos)
- **12000**: Modais filhos (abrem a partir de DeviceDetailsModal):
  - AlarmConfigModal
  - ConnectivityMapModal
  - PortActionsModal
- **13000**: Modais de nível superior (devem sempre ficar por cima):
  - **PortTrafficModal** (z-index: 13000)

### Regras

1. **Modais Base** (10000-11000): Modais principais que abrem diretamente da interface
2. **Modais Filho** (12000): Modais que abrem a partir de outros modais
3. **Modais Overlay** (13000+): Modais que devem sempre ficar por cima de tudo

### Como Adicionar Novo Modal

```css
/* Modal base (abre da interface principal) */
.my-modal-overlay {
  z-index: 10000; /* ou 11000 se for modal de dispositivo */
}

/* Modal filho (abre de outro modal) */
.my-child-modal-overlay {
  z-index: 12000;
}

/* Modal overlay (sempre por cima) */
.my-overlay-modal {
  z-index: 13000;
}
```

### Estrutura Atual

```
┌─ z-index: 13000 ─────────────────────────┐
│ PortTrafficModal                         │ ← Sempre visível
├─ z-index: 12000 ─────────────────────────┤
│ AlarmConfigModal                         │
│ ConnectivityMapModal                     │ ← Filhos de DeviceDetailsModal
│ PortActionsModal                         │
├─ z-index: 11000 ─────────────────────────┤
│ DeviceDetailsModal                       │ ← Modal de dispositivo
├─ z-index: 10000 ─────────────────────────┤
│ SiteDetailsModal                         │ ← Modal de site
└──────────────────────────────────────────┘
```

## Atualizado em: 2026-01-24
