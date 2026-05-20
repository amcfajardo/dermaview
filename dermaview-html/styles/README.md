# DermaView CSS Architecture

This folder contains organized, modular CSS files for the DermaView application.

## File Structure

```
styles/
├── global.css           # Root variables, resets, typography, utilities
├── header.css           # Header, navigation, brand styling
├── hero.css             # Hero section and features grid
├── buttons.css          # Primary and secondary button styles
├── cards.css            # Panel cards and alert boxes
├── procedures.css       # Procedures list and card styles
├── upload.css           # Image upload and preview styles
├── treatment.css        # Treatment comparison and results visualization
└── responsive.css       # Media queries and responsive design
```

## File Descriptions

### `global.css`
Contains:
- CSS custom properties (variables) for colors, spacing, shadows, and transitions
- CSS reset and base element styles
- Utility classes (section-grid, grid-2, detail-list, empty-state)
- Global typography defaults

### `header.css`
Contains:
- `.site-header` - Sticky navigation bar styling
- `.header-inner` - Header container layout
- `.brand` and `.brand-mark` - Logo styling
- `.top-nav` - Navigation menu styling
- `.app-content` - Main content container

### `hero.css`
Contains:
- `.hero` and `.hero-grid` - Hero section layout
- `.hero-headline` - Large display text styling
- `.hero-copy` - Body text styling
- `.status-badge` - Pill badge component
- `.section-heading` - Section title styling
- `.features-grid` and `.feature-card` - Feature cards layout and styling

### `buttons.css`
Contains:
- `.button` - Primary button with gradient
- `.button-secondary` - Secondary outline button
- Hover and active states for all button variants

### `cards.css`
Contains:
- `.panel-card` - Main card/panel component with sticky positioning
- `.alert-box` - Warning/alert message styling

### `procedures.css`
Contains:
- `.procedure-card` - Interactive procedure selection cards
- `.procedure-card.selected` - Active state styling
- `.procedure-chip` - Category badge styling

### `upload.css`
Contains:
- `.upload-panel` - Upload container
- `.upload-box` - Drag-and-drop area styling
- `.upload-preview` - Image preview container
- Fade-in animation for preview

### `treatment.css`
Contains:
- `.comparison-grid` - Before/after image comparison layout
- `.image-card` - Individual image card styling
- `.stat-grid` and `.stat-card` - Statistics display
- `.recommendation-list` - Treatment recommendations styling

### `responsive.css`
Contains:
- Media queries for tablet (900px)
- Media queries for mobile (640px)
- Landscape mode adjustments
- High DPI screen optimizations
- Reduced motion preferences
- Dark mode support structure (ready for future implementation)

## CSS Variables

Key CSS variables defined in `global.css`:

```css
/* Colors */
--color-primary: #2563eb
--color-secondary: #7c3aed
--color-text: #111827
--color-border: #e5e7eb
--color-bg: #eef3ff

/* Spacing */
--spacing-xs: 8px
--spacing-sm: 12px
--spacing-md: 16px
--spacing-lg: 24px
--spacing-xl: 32px

/* Border Radius */
--radius-sm: 12px
--radius-md: 14px
--radius-xl: 20px
--radius-3xl: 24px
--radius-full: 999px

/* Shadows */
--shadow-sm: 0 18px 60px rgba(15, 23, 42, 0.06)
--shadow-md: 0 24px 80px rgba(15, 23, 42, 0.08)
--shadow-hover: 0 18px 40px rgba(37, 99, 235, 0.12)

/* Transitions */
--transition-fast: 180ms ease
--transition-normal: 300ms ease
```

## Import Order

The CSS files are imported in `index.html` in the following order:

1. **global.css** - Must be first (defines variables)
2. **header.css** - Layout foundation
3. **hero.css** - Hero components
4. **buttons.css** - Button styles
5. **cards.css** - Card components
6. **procedures.css** - Procedures page
7. **upload.css** - Upload components
8. **treatment.css** - Treatment visualization
9. **responsive.css** - Media queries (must be last)

## Maintenance Guidelines

- **Variables First**: Always use CSS variables when adding new styles
- **Mobile First**: Add mobile styles in component files, use media queries in responsive.css
- **Consistency**: Follow the established naming conventions and spacing scale
- **Accessibility**: Ensure sufficient color contrast and interactive states
- **Performance**: Avoid duplicate selectors across files

## Future Enhancements

- Dark mode color schemes (structure ready in responsive.css)
- Additional animation presets
- Accessibility improvements (ARIA attributes)
- CSS grid or flexbox layout system expansion
