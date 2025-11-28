# Modelagem de Infraestrutura Óptica - Hierarquia Física

**Data**: 28 de novembro de 2025  
**Versão**: 1.0.0  
**Status**: 📋 Planejamento (Não Implementado)

---

## 1. Visão Geral do Modelo

Esta é uma mudança arquitetural fundamental. Sair de uma "contagem simples" para uma **Hierarquia Física** é o que diferencia um sistema de inventário básico de um software de engenharia de rede (como o ConnectMaster ou Smallworld).

### Objetivo

Representar a realidade física do cabo para permitir operações precisas de **fusão** e **manobra**.

### Hierarquia Proposta

```
📦 FiberProfile (Perfil)
   └─ Gabarito de fábrica (ex: "Cabo 48FO Padrão")
      └─ Define: total_fibers, tube_count, fibers_per_tube

🌑 FiberCable (Cabo)
   └─ Item físico lançado na rua
      └─ Instância de um FiberProfile
         └─ Gerado automaticamente ao criar cabo

🧪 BufferTube (Tubo Loose)
   └─ Subdivisão colorida dentro do cabo
      └─ Contém múltiplas fibras
         └─ Identificado por número e cor

〰️ FiberStrand (Filamento)
   └─ A fibra de vidro em si
      └─ Identificado por número e cor dentro do tubo
         └─ Pode estar conectado a Port ou fusionado a outra fibra
```

---

## 2. Implementação no Backend (Django)

### A. Modelos Propostos

Arquivo: `backend/inventory/models.py`

```python
from django.db import models

class FiberProfile(models.Model):
    """
    Define o gabarito de construção do cabo (template de fábrica).
    
    Exemplo: "48FO (4x12)" significa 4 tubos com 12 fibras cada.
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Ex: '48FO (4x12)', '144FO (12x12)'"
    )
    total_fibers = models.IntegerField(
        help_text="Total de fibras no cabo"
    )
    tube_count = models.IntegerField(
        help_text="Quantos tubos loose o cabo possui"
    )
    fibers_per_tube = models.IntegerField(
        help_text="Quantas fibras dentro de cada tubo"
    )
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        help_text="Fabricante do cabo (Furukawa, Prysmian, etc.)"
    )
    
    class Meta:
        db_table = "inventory_fiber_profile"
        ordering = ["total_fibers", "name"]
    
    def __str__(self):
        return f"{self.name} ({self.total_fibers}FO)"
    
    def clean(self):
        """Valida que tube_count * fibers_per_tube = total_fibers"""
        if self.tube_count * self.fibers_per_tube != self.total_fibers:
            raise ValidationError(
                f"Inconsistência: {self.tube_count} tubos x "
                f"{self.fibers_per_tube} fibras = "
                f"{self.tube_count * self.fibers_per_tube}, "
                f"mas total_fibers={self.total_fibers}"
            )


class FiberCable(models.Model):
    """
    A instância física do cabo lançado na infraestrutura.
    """
    name = models.CharField(max_length=100, unique=True)
    
    profile = models.ForeignKey(
        FiberProfile,
        on_delete=models.PROTECT,
        related_name="cables",
        help_text="Perfil técnico do cabo (define estrutura interna)"
    )
    
    site_a = models.ForeignKey(
        'Site',
        related_name='cables_start',
        on_delete=models.CASCADE,
        help_text="Site de origem"
    )
    
    site_b = models.ForeignKey(
        'Site',
        related_name='cables_end',
        on_delete=models.CASCADE,
        help_text="Site de destino"
    )
    
    length_meters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Comprimento físico do cabo em metros"
    )
    
    # Campos espaciais mantidos da estrutura atual
    path_coordinates = models.JSONField(
        blank=True,
        null=True,
        help_text="Coordenadas do traçado KML"
    )
    
    path = models.LineStringField(
        srid=4326,
        blank=True,
        null=True,
        help_text="Geometria PostGIS para consultas espaciais"
    )
    
    status = models.CharField(
        max_length=15,
        choices=[
            ('planned', 'Planejado'),
            ('active', 'Ativo (Iluminado)'),
            ('dark', 'Fibra Apagada (Dark Fiber)'),
            ('cut', 'Rompido (Crítico)'),
        ],
        default='planned'
    )
    
    installed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Data de instalação física"
    )
    
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = "inventory_fiber_cable"
        ordering = ["name"]
    
    def __str__(self):
        return f"{self.name} ({self.profile.name})"
    
    def create_structure(self):
        """
        Gera tubos e fibras automaticamente baseado no perfil.
        Chamado após criação do cabo ou mudança de perfil.
        """
        # Limpa estrutura existente se houver
        self.tubes.all().delete()
        
        # Cria tubos
        for tube_num in range(1, self.profile.tube_count + 1):
            tube = BufferTube.objects.create(
                cable=self,
                number=tube_num,
                color=get_tube_color_name(tube_num)
            )
            
            # Cria fibras dentro do tubo
            for fiber_num in range(1, self.profile.fibers_per_tube + 1):
                FiberStrand.objects.create(
                    tube=tube,
                    number=fiber_num,
                    color=get_fiber_color_name(fiber_num),
                    status='dark'  # Padrão: apagada
                )


class BufferTube(models.Model):
    """
    Tubo Loose (unidade de proteção que agrupa fibras).
    Segue padrão de cores ABNT NBR 14565.
    """
    cable = models.ForeignKey(
        FiberCable,
        related_name='tubes',
        on_delete=models.CASCADE
    )
    
    number = models.IntegerField(
        help_text="Número sequencial do tubo (1, 2, 3...)"
    )
    
    color = models.CharField(
        max_length=20,
        help_text="Cor do tubo conforme padrão (verde, amarelo, branco...)"
    )
    
    class Meta:
        db_table = "inventory_buffer_tube"
        ordering = ["cable", "number"]
        unique_together = [["cable", "number"]]
    
    def __str__(self):
        return f"{self.cable.name} - Tubo {self.number} ({self.color})"


class FiberStrand(models.Model):
    """
    O fio de fibra individual (filamento de vidro).
    Esta é a unidade atômica do sistema de gerenciamento.
    """
    tube = models.ForeignKey(
        BufferTube,
        related_name='strands',
        on_delete=models.CASCADE
    )
    
    number = models.IntegerField(
        help_text="Número da fibra dentro do tubo (1-12 tipicamente)"
    )
    
    color = models.CharField(
        max_length=20,
        help_text="Cor da fibra conforme padrão"
    )
    
    status = models.CharField(
        max_length=15,
        choices=[
            ('dark', 'Apagada (Dark Fiber)'),
            ('lit', 'Iluminada (Ativa)'),
            ('broken', 'Rompida'),
            ('reserved', 'Reservada'),
        ],
        default='dark'
    )
    
    # CONEXÕES FÍSICAS (aqui está o segredo da modelagem)
    
    connected_device_port = models.OneToOneField(
        'Port',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='connected_fiber',
        help_text="Porta de dispositivo conectada (DIO, ODF, Switch)"
    )
    
    fused_to = models.OneToOneField(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='fusion_pair',
        help_text="Fibra com a qual esta está fusionada (emenda)"
    )
    
    # Metadados de qualidade (medições ópticas)
    attenuation_db = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Atenuação medida em dB"
    )
    
    last_test_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Última medição OTDR"
    )
    
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = "inventory_fiber_strand"
        ordering = ["tube__cable", "tube__number", "number"]
        unique_together = [["tube", "number"]]
    
    def __str__(self):
        return (
            f"{self.tube.cable.name} - "
            f"T{self.tube.number}F{self.number} ({self.color})"
        )
    
    @property
    def full_address(self):
        """Endereço completo da fibra (para documentação)"""
        return {
            "cable": self.tube.cable.name,
            "tube": self.tube.number,
            "tube_color": self.tube.color,
            "fiber": self.number,
            "fiber_color": self.color,
            "notation": f"T{self.tube.number}F{self.number}"
        }
```

### B. Funções Auxiliares (Padrão de Cores)

Arquivo: `backend/inventory/utils/fiber_colors.py`

```python
"""
Padrão de cores para fibras ópticas conforme ABNT NBR 14565 / TIA-598.
Sequência de 1 a 12 se repete para tubos e fibras.
"""

FIBER_COLOR_MAP = {
    1: {"name": "Verde", "hex": "#009900", "rgb": (0, 153, 0)},
    2: {"name": "Amarelo", "hex": "#FFFF00", "rgb": (255, 255, 0)},
    3: {"name": "Branco", "hex": "#FFFFFF", "rgb": (255, 255, 255)},
    4: {"name": "Azul", "hex": "#0000FF", "rgb": (0, 0, 255)},
    5: {"name": "Vermelho", "hex": "#FF0000", "rgb": (255, 0, 0)},
    6: {"name": "Violeta", "hex": "#800080", "rgb": (128, 0, 128)},
    7: {"name": "Marrom", "hex": "#A52A2A", "rgb": (165, 42, 42)},
    8: {"name": "Rosa", "hex": "#FFC0CB", "rgb": (255, 192, 203)},
    9: {"name": "Preto", "hex": "#000000", "rgb": (0, 0, 0)},
    10: {"name": "Cinza", "hex": "#808080", "rgb": (128, 128, 128)},
    11: {"name": "Laranja", "hex": "#FFA500", "rgb": (255, 165, 0)},
    12: {"name": "Aqua", "hex": "#00FFFF", "rgb": (0, 255, 255)},
}


def get_fiber_color_name(position: int) -> str:
    """Retorna nome da cor para uma posição (1-indexed)."""
    normalized = ((position - 1) % 12) + 1
    return FIBER_COLOR_MAP[normalized]["name"]


def get_fiber_color_hex(position: int) -> str:
    """Retorna código hexadecimal da cor."""
    normalized = ((position - 1) % 12) + 1
    return FIBER_COLOR_MAP[normalized]["hex"]


def get_tube_color_name(position: int) -> str:
    """
    Tubos seguem o mesmo padrão de cores das fibras.
    Para mais de 12 tubos, a norma pede marcação adicional (risco preto).
    """
    return get_fiber_color_name(position)


def get_tube_color_hex(position: int) -> str:
    """Retorna cor hexadecimal do tubo."""
    return get_fiber_color_hex(position)
```

---

## 3. Padrão de Cores (Tabela de Referência)

Seguindo o padrão de mercado (**ABNT NBR 14565** / **TIA-598**), a sequência de 1 a 12 se repete.

| ID  | Cor       | Código Hex | Emoji | Nome        |
| --- | --------- | ---------- | ----- | ----------- |
| 1   | Verde     | `#009900`  | 🟢    | Verde       |
| 2   | Amarelo   | `#FFFF00`  | 🟡    | Amarelo     |
| 3   | Branco    | `#FFFFFF`  | ⚪    | Branco      |
| 4   | Azul      | `#0000FF`  | 🔵    | Azul        |
| 5   | Vermelho  | `#FF0000`  | 🔴    | Vermelho    |
| 6   | Violeta   | `#800080`  | 🟣    | Violeta     |
| 7   | Marrom    | `#A52A2A`  | 🟤    | Marrom      |
| 8   | Rosa      | `#FFC0CB`  | 🌸    | Rosa        |
| 9   | Preto     | `#000000`  | ⚫    | Preto       |
| 10  | Cinza     | `#808080`  | 🔘    | Cinza       |
| 11  | Laranja   | `#FFA500`  | 🟠    | Laranja     |
| 12  | Aqua      | `#00FFFF`  | 💧    | Aqua/Turquesa |

**Nota**: Se o cabo for **144FO (12 tubos x 12 fibras)**, a lógica funciona perfeitamente. Se tiver mais de 12 tubos, a norma pede uma marcação (risco preto) no tubo, mas a cor base se repete.

---

## 4. Frontend - Visualização de Estrutura Física

### A. Arquivo de Cores (Compartilhado)

Arquivo: `frontend/src/utils/fiberColors.js`

```javascript
/**
 * Padrão de cores ABNT NBR 14565 / TIA-598
 * Usado para tubos e fibras ópticas
 */
export const FIBER_COLOR_MAP = {
  1: { name: 'Verde', hex: '#009900', emoji: '🟢' },
  2: { name: 'Amarelo', hex: '#FFFF00', emoji: '🟡' },
  3: { name: 'Branco', hex: '#FFFFFF', emoji: '⚪' },
  4: { name: 'Azul', hex: '#0000FF', emoji: '🔵' },
  5: { name: 'Vermelho', hex: '#FF0000', emoji: '🔴' },
  6: { name: 'Violeta', hex: '#800080', emoji: '🟣' },
  7: { name: 'Marrom', hex: '#A52A2A', emoji: '🟤' },
  8: { name: 'Rosa', hex: '#FFC0CB', emoji: '🌸' },
  9: { name: 'Preto', hex: '#000000', emoji: '⚫' },
  10: { name: 'Cinza', hex: '#808080', emoji: '🔘' },
  11: { name: 'Laranja', hex: '#FFA500', emoji: '🟠' },
  12: { name: 'Aqua', hex: '#00FFFF', emoji: '💧' },
};

/**
 * Retorna cor para uma posição (1-indexed, repetição cíclica)
 */
export function getFiberColor(position) {
  const normalized = ((position - 1) % 12) + 1;
  return FIBER_COLOR_MAP[normalized];
}

/**
 * Retorna lista de cores para selector
 */
export function getAllColors() {
  return Object.values(FIBER_COLOR_MAP);
}
```

### B. Componente de Visualização (Cross-Section View)

Arquivo: `frontend/src/components/Inventory/Fiber/CableStructureView.vue`

```vue
<template>
  <div class="border rounded-xl p-4 bg-gray-50 dark:bg-gray-900">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-bold text-gray-700 dark:text-gray-300">
        Estrutura Física: {{ cableName }}
      </h3>
      <span class="text-xs text-gray-500">
        {{ totalFibers }} fibras ({{ tubeCount }} tubos × {{ fibersPerTube }})
      </span>
    </div>

    <div class="flex flex-wrap gap-6 justify-center">
      <div 
        v-for="tube in tubes" 
        :key="tube.id"
        class="flex flex-col items-center"
      >
        <!-- Representação visual do tubo (círculo) -->
        <div 
          class="w-24 h-24 rounded-full border-4 flex flex-wrap items-center justify-center p-2 gap-1 bg-white dark:bg-gray-800 shadow-sm relative transition-transform hover:scale-105 cursor-pointer"
          :style="{ borderColor: tube.hexColor }"
          @click="$emit('select-tube', tube)"
        >
          <!-- Badge do número do tubo -->
          <span 
            class="absolute -top-3 bg-gray-800 dark:bg-gray-700 text-white text-[10px] px-2 py-0.5 rounded-full font-bold"
          >
            T{{ tube.number }}
          </span>

          <!-- Fibras dentro do tubo (círculos menores) -->
          <div 
            v-for="fiber in tube.fibers" 
            :key="fiber.id"
            class="w-4 h-4 rounded-full border border-gray-300 dark:border-gray-600 shadow-sm cursor-pointer transition-all hover:ring-2 hover:ring-indigo-500 hover:scale-110"
            :class="{
              'opacity-50': fiber.status === 'dark',
              'ring-2 ring-green-500': fiber.status === 'lit',
              'ring-2 ring-red-500': fiber.status === 'broken'
            }"
            :style="{ backgroundColor: fiber.hexColor }"
            :title="`Fibra ${fiber.number} (${fiber.colorName}) - ${getStatusLabel(fiber.status)}`"
            @click.stop="$emit('select-fiber', fiber)"
          >
            <!-- Indicador de conexão (pequeno ponto) -->
            <div 
              v-if="fiber.connected || fiber.fused"
              class="w-1.5 h-1.5 rounded-full bg-white absolute top-0.5 right-0.5 shadow-sm"
            ></div>
          </div>
        </div>
        
        <!-- Label do tubo -->
        <span class="text-xs mt-2 font-medium text-gray-600 dark:text-gray-400">
          {{ tube.colorName }}
        </span>
        
        <!-- Status de ocupação do tubo -->
        <span class="text-[10px] text-gray-500">
          {{ tube.usedCount }}/{{ tube.totalCount }} em uso
        </span>
      </div>
    </div>

    <!-- Legenda de status -->
    <div class="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700 flex gap-4 justify-center text-xs">
      <div class="flex items-center gap-1">
        <div class="w-3 h-3 rounded-full bg-gray-300 opacity-50"></div>
        <span class="text-gray-600 dark:text-gray-400">Apagada</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-3 h-3 rounded-full bg-green-500 ring-2 ring-green-500"></div>
        <span class="text-gray-600 dark:text-gray-400">Iluminada</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-3 h-3 rounded-full bg-red-500 ring-2 ring-red-500"></div>
        <span class="text-gray-600 dark:text-gray-400">Rompida</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { getFiberColor } from '@/utils/fiberColors';

const props = defineProps({
  cableName: { type: String, required: true },
  tubes: { type: Array, required: true },
  // Formato esperado:
  // [
  //   {
  //     id: 101,
  //     number: 1,
  //     color: 'Verde',
  //     hexColor: '#009900',
  //     fibers: [
  //       { id: 1, number: 1, color: 'Verde', hexColor: '#009900', status: 'lit', connected: true, fused: false },
  //       ...
  //     ]
  //   }
  // ]
});

defineEmits(['select-tube', 'select-fiber']);

const totalFibers = computed(() => {
  return props.tubes.reduce((sum, tube) => sum + tube.fibers.length, 0);
});

const tubeCount = computed(() => props.tubes.length);

const fibersPerTube = computed(() => {
  return props.tubes[0]?.fibers.length || 0;
});

function getStatusLabel(status) {
  const labels = {
    dark: 'Apagada',
    lit: 'Iluminada (Ativa)',
    broken: 'Rompida',
    reserved: 'Reservada'
  };
  return labels[status] || status;
}
</script>
```

---

## 5. Casos de Uso (Cenários Reais)

### Cenário 1: Técnico no Poste fazendo Fusão

**Contexto**: Técnico abre CEO-01 (Caixa de Emenda Óptica) para conectar cliente.

**Passos no Sistema**:

1. Abrir CEO-01 no mapa
2. Sistema mostra:
   - **Entrada**: Cabo Backbone (48FO) vindo do POP
   - **Saída**: Cabo Drop (12FO) indo para Cliente X
3. Técnico precisa fundir para ativar o serviço
4. **Ação no App**:
   - Selecionar **Cabo Backbone** → **Tubo Verde (T1)** → **Fibra Azul (F4)**
   - Selecionar **Cabo Drop** → **Tubo Único (T1)** → **Fibra Azul (F4)**
   - Clicar em **"Registrar Fusão"**
5. **Backend**: Cria registro `FiberStrand.fused_to` vinculando as duas fibras
6. **Resultado**: Dashboard mostra fibra iluminada, documentação atualizada

### Cenário 2: Técnico no Data Center (DIO)

**Contexto**: Iluminar porta do switch para novo cliente corporativo.

**Passos no Sistema**:

1. Acessar DIO-Rack-01 no inventário
2. Selecionar **Porta 1 do DIO**
3. Sistema mostra fibras disponíveis do **Cabo de Chegada**
4. **Ação no App**:
   - Selecionar **Cabo Backbone** → **Tubo Verde (T1)** → **Fibra Verde (F1)**
   - Clicar em **"Conectar à Porta DIO-01"**
5. Conectar **Patch Cord** entre DIO-01 e Switch Port Gig0/1
6. **Backend**: Cria vínculo `FiberStrand.connected_device_port = Port(Switch Gig0/1)`
7. **Resultado**: Circuito lógico completo documentado

### Cenário 3: Expansão de Capacidade

**Contexto**: Rede está crescendo, precisa adicionar cabo novo.

**Passos no Sistema**:

1. Criar novo `FiberProfile`: "144FO (12x12)"
2. Criar `FiberCable` instanciando o perfil
3. Sistema chama automaticamente `create_structure()`
4. **Resultado**: 12 tubos com 12 fibras cada (144 total) criados e prontos para uso

---

## 6. Migração de Dados (Estratégia)

### Estado Atual

```python
# Estrutura simples atual
FiberCable:
  - origin_port (FK to Port)
  - destination_port (FK to Port)
  - fiber_count (int)  # Ex: 48
```

### Estado Futuro

```python
# Estrutura hierárquica
FiberCable:
  - profile (FK to FiberProfile)
  - tubes (RelatedManager → BufferTube)

BufferTube:
  - strands (RelatedManager → FiberStrand)

FiberStrand:
  - connected_device_port (FK to Port)
  - fused_to (self-referential FK)
```

### Script de Migração

Arquivo: `backend/inventory/migrations/0XXX_fiber_hierarchy.py`

```python
from django.db import migrations

def migrate_existing_cables(apps, schema_editor):
    """
    Converte cabos legados para nova estrutura hierárquica.
    """
    FiberCable = apps.get_model('inventory', 'FiberCable')
    FiberProfile = apps.get_model('inventory', 'FiberProfile')
    
    # Criar perfis padrão se não existirem
    profiles = {
        12: FiberProfile.objects.get_or_create(
            name="12FO (1x12)",
            defaults={"total_fibers": 12, "tube_count": 1, "fibers_per_tube": 12}
        )[0],
        24: FiberProfile.objects.get_or_create(
            name="24FO (2x12)",
            defaults={"total_fibers": 24, "tube_count": 2, "fibers_per_tube": 12}
        )[0],
        48: FiberProfile.objects.get_or_create(
            name="48FO (4x12)",
            defaults={"total_fibers": 48, "tube_count": 4, "fibers_per_tube": 12}
        )[0],
    }
    
    # Migrar cabos existentes
    for cable in FiberCable.objects.all():
        # Inferir perfil baseado em fiber_count (campo legado)
        fiber_count = getattr(cable, 'fiber_count', None) or 48
        profile = profiles.get(fiber_count, profiles[48])
        
        cable.profile = profile
        cable.save()
        
        # Gerar estrutura física
        cable.create_structure()
        
        # Se havia conexão origin_port/destination_port, conectar primeira fibra
        if hasattr(cable, 'origin_port') and cable.origin_port:
            first_strand = cable.tubes.first().strands.first()
            first_strand.connected_device_port = cable.origin_port
            first_strand.status = 'lit'
            first_strand.save()

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0XXX_previous_migration'),
    ]
    
    operations = [
        # Criar tabelas
        migrations.CreateModel(...),
        
        # Migrar dados
        migrations.RunPython(migrate_existing_cables),
    ]
```

---

## 7. Endpoints de API (Backend)

### A. Listar Estrutura de Cabo

**Endpoint**: `GET /api/v1/fiber-cables/{cable_id}/structure/`

**Response**:
```json
{
  "cable_id": 123,
  "name": "Backbone CDT-Elagro",
  "profile": {
    "id": 3,
    "name": "48FO (4x12)",
    "total_fibers": 48
  },
  "tubes": [
    {
      "id": 101,
      "number": 1,
      "color": "Verde",
      "hex_color": "#009900",
      "fibers": [
        {
          "id": 1001,
          "number": 1,
          "color": "Verde",
          "hex_color": "#009900",
          "status": "lit",
          "connected_port": {
            "id": 42,
            "name": "Gig0/1",
            "device": "Switch-CDT"
          },
          "fused_to": null,
          "attenuation_db": 0.35
        },
        // ... 11 mais fibras
      ],
      "usage": {
        "total": 12,
        "used": 3,
        "available": 9
      }
    },
    // ... 3 mais tubos
  ],
  "summary": {
    "total_fibers": 48,
    "lit_fibers": 12,
    "dark_fibers": 35,
    "broken_fibers": 1,
    "utilization_percent": 25.0
  }
}
```

### B. Registrar Fusão

**Endpoint**: `POST /api/v1/fiber-strands/fusion/`

**Request**:
```json
{
  "fiber_a_id": 1001,
  "fiber_b_id": 2005,
  "fusion_location": "CEO-01 (Poste 12345)",
  "technician": "João Silva",
  "attenuation_db": 0.15
}
```

**Response**:
```json
{
  "status": "ok",
  "fusion_id": 789,
  "fiber_a": {
    "address": "Cabo Backbone - T1F4 (Tubo Verde, Fibra Azul)",
    "status": "lit"
  },
  "fiber_b": {
    "address": "Cabo Drop - T1F4 (Tubo Verde, Fibra Azul)",
    "status": "lit"
  },
  "total_attenuation": 0.15
}
```

### C. Conectar Fibra a Porta

**Endpoint**: `POST /api/v1/fiber-strands/{strand_id}/connect/`

**Request**:
```json
{
  "port_id": 42,
  "connection_type": "dio",
  "notes": "DIO Rack-01 Porta 12"
}
```

**Response**:
```json
{
  "status": "ok",
  "fiber": {
    "address": "Cabo Backbone - T1F1 (Tubo Verde, Fibra Verde)",
    "status": "lit"
  },
  "port": {
    "id": 42,
    "name": "Gig0/1",
    "device": "Switch-CDT",
    "site": "CDT"
  }
}
```

---

## 8. Impactos e Benefícios

### ✅ Benefícios

1. **Documentação Precisa**
   - Rastreabilidade completa de cada fibra individual
   - Histórico de fusões e manobras
   - Conformidade com normas técnicas (ABNT/TIA)

2. **Redução de Erros Operacionais**
   - Técnico sabe exatamente qual fibra usar
   - Evita rompimento por identificação errada
   - Validação automática de disponibilidade

3. **Planejamento de Capacidade**
   - Dashboard mostra fibras disponíveis em tempo real
   - Alertas quando cabos atingem 80% de ocupação
   - Projeções de crescimento baseadas em uso real

4. **Integração OTDR**
   - Armazenar medições de atenuação por fibra
   - Histórico de qualidade do sinal
   - Detecção precoce de degradação

5. **Relatórios Profissionais**
   - Documentação as-built automática
   - Exportação para CAD/GIS
   - Certificação de instalação

### ⚠️ Desafios

1. **Migração de Dados**
   - Cabos existentes precisam ser convertidos
   - Pode exigir levantamento de campo para validar tubos/fibras

2. **Complexidade da Interface**
   - UI precisa ser intuitiva para técnicos em campo
   - Versão mobile otimizada essencial

3. **Performance**
   - Queries mais complexas (3 níveis de hierarquia)
   - Necessário cache agressivo e índices otimizados

4. **Treinamento**
   - Equipe precisa entender novo modelo
   - Processo de criação de cabos muda completamente

---

## 9. Cronograma de Implementação (Sugerido)

### Fase 1: Backend (2-3 semanas)
- [ ] Criar modelos `FiberProfile`, `BufferTube`, `FiberStrand`
- [ ] Migration para estrutura hierárquica
- [ ] Script de migração de dados legados
- [ ] Serializers e endpoints de API
- [ ] Testes unitários (coverage > 80%)

### Fase 2: Frontend - Visualização (2 semanas)
- [ ] Componente `CableStructureView.vue`
- [ ] Componente `FiberSelector.vue` (picker de fibra)
- [ ] Integração com modal de cabos
- [ ] Preview de estrutura física ao criar cabo

### Fase 3: Frontend - Operações (2 semanas)
- [ ] Workflow de fusão de fibras
- [ ] Workflow de conexão a portas
- [ ] Dashboard de capacidade por cabo
- [ ] Filtros e busca por fibra específica

### Fase 4: Integrações (1 semana)
- [ ] Exportação as-built (PDF)
- [ ] API REST pública (documentação Swagger)
- [ ] Webhook para eventos de fusão/conexão
- [ ] Integração com sistema de tickets (opcional)

### Fase 5: Rollout (1 semana)
- [ ] Treinamento de equipe
- [ ] Documentação de usuário
- [ ] Deploy em ambiente de produção
- [ ] Monitoramento pós-deploy

**Total Estimado**: 8-9 semanas (2 meses)

---

## 10. Referências Técnicas

- **ABNT NBR 14565**: Cabeamento de telecomunicações para edifícios comerciais
- **TIA-598**: Optical Fiber Cable Color Coding
- **Padrão Telebrás**: Documentação histórica de infraestrutura óptica brasileira
- **ConnectMaster**: Software comercial de referência (Bentley Systems)
- **Smallworld**: GIS de utilities (GE Digital)

---

## 11. Decisão de Implementação

**Status Atual**: 📋 **Aguardando Aprovação**

Esta documentação serve como base para discussão arquitetural. Antes de iniciar a implementação, é necessário:

1. ✅ Aprovação do modelo hierárquico
2. ✅ Validação da estratégia de migração
3. ✅ Confirmação de priorização no roadmap
4. ✅ Alocação de recursos de desenvolvimento

**Próximos Passos**:
- [ ] Review técnico com time de backend
- [ ] Review de UX com time de frontend
- [ ] POC (Proof of Concept) com 1 cabo de teste
- [ ] Aprovação final para implementação completa

---

**Documento elaborado por**: GitHub Copilot  
**Revisão**: Pendente  
**Última atualização**: 28/11/2025
