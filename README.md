# Whiteboard Application

A powerful, infinite canvas whiteboard application built with PyQt6, featuring advanced zoom and navigation capabilities, note management, and session persistence.

## Features

### Core Functionality

- **Infinite Canvas**: Expandable workspace that grows automatically as you add content
- **Note Management**: Create, edit, and style notes with rich text formatting
- **Connection System**: Link notes together with visual connections
- **Session Management**: Save and load your work with automatic backup
- **Auto-save**: Automatic saving with configurable intervals

### Zoom and Navigation

- **Multi-level Zoom**: Smooth zooming from 10% to 1000% with precise control
- **Zoom-to-Cursor**: Intelligent zooming that maintains cursor position
- **Keyboard Navigation**: Comprehensive keyboard shortcuts for efficient navigation
- **Adaptive Panning**: Pan distance adjusts based on zoom level for optimal user experience
- **Multiple Pan Methods**: Mouse, keyboard, and gesture-based navigation

## Keyboard Shortcuts

### Zoom Controls

- **Ctrl + Plus (+)**: Zoom in
- **Ctrl + Minus (-)**: Zoom out
- **Ctrl + 0**: Reset zoom to 100% (Actual Size)
- **Ctrl + 9**: Fit content to window
- **Mouse Wheel + Ctrl**: Zoom in/out at cursor position

### Navigation Controls

- **Arrow Keys**: Pan the canvas in the corresponding direction
  - **Left Arrow**: Pan left
  - **Right Arrow**: Pan right
  - **Up Arrow**: Pan up
  - **Down Arrow**: Pan down
- **Ctrl + H**: Center view on content
- **Home**: Reset view to origin
- **Space + Drag**: Hold Space and drag with mouse to pan freely
- **Middle Mouse Button + Drag**: Pan the canvas
- **Shift + Left Click + Drag**: Alternative pan mode

### File Operations

- **Ctrl + N**: New whiteboard
- **Ctrl + O**: Open file
- **Ctrl + S**: Save current work
- **Ctrl + Shift + S**: Save as new file
- **Ctrl + Q**: Quit application

### Edit Operations

- **Ctrl + Z**: Undo (when implemented)
- **Ctrl + Y**: Redo (when implemented)
- **Ctrl + X**: Cut (when implemented)
- **Ctrl + C**: Copy (when implemented)
- **Ctrl + V**: Paste (when implemented)
- **Ctrl + A**: Select all (when implemented)

### View Controls

- **F11**: Toggle fullscreen mode

## Navigation Features

### Adaptive Panning

The application features intelligent panning that adjusts based on your current zoom level:

- At high zoom levels: Smaller pan distances for precise navigation
- At low zoom levels: Larger pan distances for quick traversal
- Pan distance is automatically clamped between 20-200 pixels for optimal experience

### Zoom-to-Cursor

When using the mouse wheel with Ctrl held down, the zoom operation maintains the cursor position, making it easy to zoom into specific areas of your work.

### Scene Expansion

The canvas automatically expands as you work:

- **Expansion Threshold**: 1000 pixels from edge
- **Expansion Amount**: 5000 pixels in each direction
- Seamless expansion without interrupting your workflow

## Technical Details

### Zoom Specifications

- **Minimum Zoom**: 10% (0.1x)
- **Maximum Zoom**: 1000% (10.0x)
- **Default Zoom**: 100% (1.0x)
- **Zoom Step**: 1.2x multiplier for smooth progression

### Auto-save Configuration

- **Default Interval**: 30 seconds
- **Configurable**: Interval can be adjusted programmatically
- **Smart Saving**: Only saves when changes are detected
- **Error Recovery**: Robust error handling with user feedback

### Session Data

The application saves:

- Canvas zoom level and position
- All notes with their positions, content, and styling
- Connections between notes
- Scene bounds and expansion state

## Installation

1. Ensure Python 3.8+ is installed
2. Install dependencies: `uv install`
3. Run the application: `make run`

## Development

### Running Tests

```bash
make test
```

### Code Quality Checks

```bash
make check
```

### Building

```bash
make build
```

## Backward Compatibility

The application maintains backward compatibility with previous session formats:

- Legacy zoom settings are automatically migrated
- Old navigation preferences are preserved
- Session files from previous versions load seamlessly

## User Interface

### Status Bar

- **Zoom Level**: Real-time zoom percentage display
- **Position**: Current view center coordinates
- **Messages**: Auto-save status and operation feedback

### Toolbar

Quick access to frequently used zoom and navigation functions with intuitive icons and tooltips.

### Menu System

Comprehensive menu structure with:

- **File**: Session management operations
- **Edit**: Content manipulation tools
- **View**: Zoom, navigation, and display options
- **Navigation**: Dedicated pan and movement controls

## Tips for Optimal Use

1. **Use Ctrl + H** to quickly center on your content when you get lost
2. **Combine zoom and pan** for precise positioning of elements
3. **Use Space + Drag** for quick, temporary panning without changing tools
4. **Take advantage of adaptive panning** - it automatically adjusts to your zoom level
5. **Use Ctrl + 9** to get an overview of all your content at once

## Troubleshooting

### Navigation Issues

- Ensure the canvas has focus for keyboard shortcuts to work
- Check that no modal dialogs are blocking input
- Verify zoom level is within supported range (10%-1000%)

### Performance

- Large canvases with many elements may affect performance
- Consider using Fit to Window (Ctrl + 9) to optimize view
- Auto-save can be disabled if causing performance issues

---

_For more information or to report issues, please refer to the project documentation or issue tracker._
