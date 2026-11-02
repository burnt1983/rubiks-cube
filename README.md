# Rubik's Cube

A 3D Rubik's cube that sits on the Linux desktop. The window is borderless
and clear. The cube is drawn with WebGL.

## Install

Needs Python 3, GTK 3, PyGObject, cairo, and WebKitGTK 4.1
(`python3-gi`, `python3-cairo`, `gir1.2-gtk-3.0`, `gir1.2-webkit2-4.1`).

```bash
git clone https://github.com/burnt1983/rubiks-cube.git
cd rubiks-cube
./install.sh
rubik-cube
```

The window position is saved as four numbers in
`~/.config/rubik-cube/window.json`. Nothing else is stored. It does not
start at login. The panel icon is a small cube, drawn by `icon.py`.

## How to turn it

| Action | What happens |
|---|---|
| Click | Turns the whole cube one quarter turn. Click above or below the middle to tip it, or left or right of the middle to yaw it. |
| Drag | Moves the window. |
| Double right-click a sticker | Turns that face. |
| Hold the right button | Closes the cube. |
| Escape | Closes the cube. |

Opening it again while it is already open brings the same window forward.

## Uninstall

```bash
./uninstall.sh
```

## Credits

The cube page uses [Three.js](https://github.com/mrdoob/three.js) r187.
The library is included in this repo and unpacked next to the page on
install. It is not downloaded. Three.js is MIT. See [NOTICE](NOTICE).

## Licence

MIT. See [LICENSE](LICENSE).
