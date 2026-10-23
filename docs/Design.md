# Sahaayak AI --- Design System

## 1. Design objective
Build a polished, trustworthy AI operations dashboard for community incident coordination. The UI should communicate clarity, calm, evidence, and responsible action.

## 2. Visual direction --- Jet Black + Hot Pink + Chartreuse
Non-negotiable visual identity: Sahaayak AI must use a bold, Gen Z, cyber-editorial aesthetic.
- **Jet Black `#0B0B0B`**: Primary background, navigation, dark canvas.
- **Hot Pink `#FF2DA8`**: Brand highlight, key interactive buttons, active navigation, accents.
- **Chartreuse `#D4FF3F`**: Secondary highlight, small status accents, badges, radar blips.
- **White `#FFFFFF`**: Primary text on dark surfaces.
- **Concrete Grey `#A7A7A7`**: Muted text, borders, dividers, secondary metadata.
- **Soft Black `#151515`**: Elevated cards, containers, secondary surfaces.
- **Borders `#262626` / `#333333`**: Crisp thin borders.

## 3. Typography
- Font family: Inter, system fallbacks. Clear typography with support for English, Hindi (Devanagari), and Marathi.

## 4. Design Tokens
```css
:root {
  --color-bg: #0B0B0B;
  --color-surface: #151515;
  --color-surface-raised: #1D1D1D;
  --color-text: #FFFFFF;
  --color-text-muted: #A7A7A7;
  --color-border: #262626;

  --color-primary: #FF2DA8;
  --color-primary-hover: #E91E93;
  --color-primary-soft: rgba(255, 45, 168, 0.12);

  --color-accent-chartreuse: #D4FF3F;
  --color-accent-chartreuse-soft: rgba(212, 255, 63, 0.12);

  --color-success: #48C78E;
  --color-warning: #F5B942;
  --color-danger: #FF5C68;
}
```
