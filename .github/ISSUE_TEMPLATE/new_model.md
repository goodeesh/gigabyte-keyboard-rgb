---
title: "New model support: [your model name here]"
labels: new-model
---

**Laptop model / name:** (e.g. Gigabyte Aorus 15BKF)

**Model code:** (from laptop bottom sticker, if known)

**`lsusb` output:**
```
paste `lsusb | grep -i gigabyte` here
```

**Attach calibration JSON:**
Drag the file produced by `gigabyte-rgb --calibrate` here.
(It's at `~/.config/gigabyte-keyboard-rgb/profiles/<VID>_<PID>.json`)

**Checklist:**
- [ ] I ran `gigabyte-rgb detect` and confirmed my keyboard shows up
- [ ] I ran `gigabyte-rgb --calibrate` and completed all prompts
- [ ] After restarting the tray, the colours shown match my keyboard
- [ ] I have attached the calibration JSON file above
