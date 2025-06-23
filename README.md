# Ursina PBR Lighting Engine

A lightweight, customizable **Physically Based Rendering (PBR) lighting engine** built with the [Ursina Game Engine](https://www.ursinaengine.org/).

This lighting engine supports:
- ✅ One **directional light** (with shadows)
- ✅ **Multiple point lights** (`n` point lights supported)
- ✅ **Basic PBR shading** using albedo, roughness, and normal maps

---

## ✨ Features

- **Directional Light with Shadows**  
  Real-time shadows are currently always enabled for the directional light. A toggle for enabling/disabling shadows is planned for future updates.

- **Point Lights**  
  Add as many point lights as you need — the shader automatically integrates their contribution into the PBR pipeline.

- **PBR Material Support**
  - `Albedo (Base Color)`
  - `Roughness`
  - `Metallic`
  *(pbr map support will be added later.)*

---

## 🚫 Limitations

- ❌ Only one directional light is supported at a time.
- ❌ Directional light shadows cannot currently be disabled.
- ❌ No support for spotlights (yet).
- ❌ No IBL (Image-Based Lighting) or reflections.
- ⚠️ Performance may degrade with many dynamic point lights on low-end systems.

---

## 🛠️ Planned Features

- [ ] Toggleable directional light shadows
- [ ] Spotlight support
- [ ] PBR map support
