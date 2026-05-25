# UI/UX Refactoring Guidelines: Veritas Sentinel Forensic Dashboard

## 1. Role & Objective
Act as an expert Frontend Developer and Creative UI/UX Motion Designer. Your objective is to refactor the dashboard for a multi-agent forensic system designed for deepfake detection. 
The UI must transcend standard flat or glassmorphic designs. It needs a dramatic, high-stakes "cyber-forensic" aesthetic. The interface should feel alive, technical, and slightly intimidating, emphasizing the system's active pursuit of digital truth.

## 2. Core Design System & Tokens

### The "Deep Void" Background
- **Base Background:** Use an ultra-dark, almost abyssal background (e.g., `#05050A` or `bg-slate-950`). 
- **Volumetric Lighting:** Instead of generic mesh gradients, create the illusion of a dark room illuminated by screens. Use harsh, low-opacity radial gradients (cyan `#00E5FF` or crimson `#FF2A2A`) that emanate from behind the dropzone and active components.
- **Data Particles (Optional):** Add a subtle, slow-moving particle system in the absolute background to represent unstructured data waiting to be analyzed.

### Typography & Glitch Mechanics
- **Font Family:** Use a highly technical, monospaced font for numbers and metadata (e.g., JetBrains Mono, Space Grotesk) paired with a sharp geometric sans-serif for main headings.
- **Dramatic Hierarchy:** The main headline should use a metallic or neon gradient. 
- **Text Animations:** Implement a "cryptographic decode" or slight glitch effect on the hero text on initial load. The text should scramble through random characters before resolving into "AI-Generated Content Detection System."

## 3. High-Drama Component Refactoring

### The Forensic Dropzone (The Core)
- **Visuals:** Design this not as a simple dotted box, but as an advanced "Targeting Reticle" or "Analysis Chamber." Use sharp corner brackets instead of rounded borders.
- **Idle State:** A slow, pulsing, breathing glow emanating from the center upload icon.
- **Hover/Drag State:** - The borders glow intensely with a neon cyan or alert amber.
  - **Dramatic Animation:** Trigger a continuous, horizontal "laser scan" line (a bright `div` with a `box-shadow` glow) that sweeps up and down the dropzone area while a file is being dragged over it, mimicking a biometric or forensic scan.

### The Multi-Agent Nodes (Bottom Cards)
- **Concept:** Do not treat these as passive buttons. Treat them as the live, active agents (Image, Video, Audio, Text) of the system.
- **Visuals:** Dark, semi-transparent panels with sharp edges. Include tiny, raw data readouts or moving progress bars inside the cards to make them look "busy."
- **Idle Animation:** A very subtle, unsynchronized pulsing glow on the border of each agent card, simulating that they are "breathing" or standing by on the network.
- **Hover State:** - The card elevates sharply.
  - A bright, focused beam of light (using CSS `radial-gradient` acting as a spotlight following the cursor) illuminates the card's surface.

### System Activity Indicators
- Add a running "terminal log" or "live feed" ticker somewhere in the UI (perhaps a narrow strip above the dropzone) displaying faux system initialization text (e.g., `[SYS] Agent initialized... [NET] Awaiting payload...`). This adds immense narrative drama to the UI.

## 4. Development Rules
- Use Framer Motion (if React) or standard CSS `@keyframes` for the scanning and glitch animations.
- Ensure animations are hardware-accelerated (`transform` and `opacity`) to prevent the dramatic effects from causing browser lag.
- The layout must remain highly functional; the dramatic flair should enhance the forensic theme, not obstruct the user from uploading a file.