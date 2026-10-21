# Component architecture

The active implementation is a 2D saved-hand playback engine. See [hand-animation-engine.md](hand-animation-engine.md) for the schema, module contracts, integration instructions and limitations.

The original root Aware Expo application remains untouched. The existing web component's /translation route opens the hand studio through VideoWorkspace; no root routing changes are needed. Frontend dependencies are React, React DOM, React Router and Lucide; SVG and requestAnimationFrame are browser APIs. Vite, TypeScript, Tailwind, Vitest and jsdom are development tooling. The previous Three.js runtime dependencies have been removed from this frontend.

The older FastAPI and research directories are retained. The 2D path runs directly from normalized saved landmark coordinates and does not invoke the older motion-retargeting scaffold, Blender or a 3D rig.
