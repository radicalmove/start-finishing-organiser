# SFO Aesthetic Baseline Design

## Goal

Carry the original Start Finishing Organiser identity into the Rust Mac and iPhone apps without copying the old web dashboard density onto every screen.

## Direction

Use an adaptive neon system. The app should feel like a calm command centre with a recognisable SFO neon identity: deep navy surfaces, electric pink and blue accents, cyan glow, softly rounded cards, compact status badges, and the existing gradient SFO icon language.

The everyday interface should be calmer than the original Python UI. Glow should signal selection, priority, connection state, or primary action rather than decorate every surface. Mac screens can be denser and more cockpit-like. iPhone screens should be quieter, touch-friendly, and focused on one main decision at a time.

## Visual Rules

- Use dark navy and blue-black as the base rather than the current warm paper/moss shell.
- Preserve pink, blue, and cyan as the product's recognisable accents.
- Keep the SFO rounded gradient mark as the foundation for app icons and launch identity.
- Use translucent dark cards with fine borders and restrained shadow/glow.
- Use compact badges for state, counts, and routing decisions, with restrained corners rather than heavy pill shapes.
- Avoid heavily pill-shaped buttons. Buttons and compact controls should have subtly rounded corners; larger panels can stay softened but should not feel blob-like.
- Keep typography practical and modern; avoid the Rust shell's serif/editorial direction for core app UI.
- Make mobile calmer by reducing density, enlarging touch targets, and using neon primarily for hierarchy.

## First Implementation Slice

Apply the baseline to the Tauri launcher shell only. This is intentionally narrow so the aesthetic can be reviewed visually before it is expanded into the mobile Today workflow, generated icons, or deeper component structure.
