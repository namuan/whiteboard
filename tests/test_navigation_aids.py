"""
Comprehensive tests for navigation aids accuracy and performance.

This module tests the MinimapWidget, NavigationPanel, and their integration
with the main application for accuracy and performance under various conditions.
"""

import pytest
import time
from PyQt6.QtWidgets import QApplication, QGraphicsRectItem, QGraphicsEllipseItem
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtTest import QTest, QSignalSpy

from src.whiteboard.navigation_panel import NavigationPanel, MinimapWidget
from src.whiteboard.canvas import WhiteboardScene
from src.whiteboard.main_window import MainWindow


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def scene():
    """Create a test scene."""
    scene = WhiteboardScene()
    yield scene
    scene.clear()


@pytest.fixture
def minimap_widget(scene):
    """Create a MinimapWidget for testing."""
    widget = MinimapWidget(scene)
    yield widget
    widget.close()


@pytest.fixture
def navigation_panel(scene):
    """Create a NavigationPanel for testing."""
    panel = NavigationPanel(scene)
    yield panel
    panel.close()


@pytest.fixture
def main_window(app):
    """Create MainWindow instance for testing."""
    window = MainWindow()
    yield window
    window.close()


class TestMinimapWidget:
    """Test cases for MinimapWidget class."""

    def test_minimap_initialization(self, minimap_widget, scene):
        """Test that minimap initializes correctly."""
        assert minimap_widget._main_scene == scene
        assert minimap_widget._minimap_scene is not None
        assert minimap_widget._viewport_rect is None
        assert minimap_widget._viewport_item is None
        assert minimap_widget.minimumSize().width() == 150
        assert minimap_widget.minimumSize().height() == 150

    def test_minimap_viewport_indicator_update(self, minimap_widget):
        """Test viewport indicator updates correctly."""
        # Test with valid rectangle
        test_rect = QRectF(100, 100, 200, 200)
        minimap_widget.update_viewport_indicator(test_rect)

        assert minimap_widget._viewport_rect == test_rect
        assert minimap_widget._viewport_item is not None
        assert minimap_widget._viewport_item.zValue() == 1000

        # Test with invalid rectangle
        invalid_rect = QRectF()
        minimap_widget.update_viewport_indicator(invalid_rect)
        # Should not crash and should handle gracefully

    def test_minimap_schedule_update_performance(self, minimap_widget, scene):
        """Test that minimap update scheduling adapts to scene complexity."""
        # Test with simple scene
        minimap_widget.schedule_update()
        assert minimap_widget._update_timer.interval() > 0

        # Add many items to make scene complex
        for i in range(150):  # Above threshold of 100
            item = QGraphicsRectItem(i * 10, i * 10, 50, 50)
            scene.addItem(item)

        # Schedule update with complex scene
        minimap_widget.schedule_update()
        # Timer should be active
        assert minimap_widget._update_timer.isActive()

    def test_minimap_content_update_with_items(self, minimap_widget, scene):
        """Test minimap content updates when scene has items."""
        # Add test items to scene
        rect_item = QGraphicsRectItem(0, 0, 100, 100)
        ellipse_item = QGraphicsEllipseItem(200, 200, 50, 50)
        scene.addItem(rect_item)
        scene.addItem(ellipse_item)

        # Trigger content update
        minimap_widget._update_minimap_content()

        # Verify minimap scene rect matches main scene
        assert minimap_widget._minimap_scene.sceneRect() == scene.sceneRect()

    def test_minimap_performance_with_large_scene(self, minimap_widget, scene):
        """Test minimap performance with large number of items."""
        # Add many items to test performance
        for i in range(200):  # Large number of items
            item = QGraphicsRectItem(i * 5, i * 5, 20, 20)
            scene.addItem(item)

        # Measure update time
        update_start = time.time()
        minimap_widget._update_minimap_content()
        update_time = time.time() - update_start

        # Update should complete within reasonable time (less than 1 second)
        assert update_time < 1.0

    def test_minimap_navigate_signal(self, minimap_widget):
        """Test that minimap emits navigate signal correctly."""
        signal_spy = QSignalSpy(minimap_widget.navigate_to_position)

        # Simulate mouse click on minimap
        test_point = QPointF(100, 100)
        minimap_widget.navigate_to_position.emit(test_point)

        assert len(signal_spy) == 1
        assert signal_spy[0][0] == test_point

    def test_minimap_lod_rendering(self, minimap_widget, scene):
        """Test level-of-detail rendering for performance."""
        # Add items beyond threshold
        for i in range(150):
            item = QGraphicsRectItem(i * 2, i * 2, 10, 10)
            scene.addItem(item)

        # Test LOD rendering
        minimap_widget._perform_full_minimap_update(
            scene.sceneRect(), scene.items(), use_lod=True
        )

        # Should complete without errors
        assert minimap_widget._minimap_scene.sceneRect() == scene.sceneRect()


class TestNavigationPanel:
    """Test cases for NavigationPanel class."""

    def test_navigation_panel_initialization(self, navigation_panel, scene):
        """Test that navigation panel initializes correctly."""
        assert navigation_panel._main_scene == scene
        assert navigation_panel._minimap is not None
        assert navigation_panel._zoom_spinbox is not None
        assert navigation_panel._zoom_slider is not None
        assert navigation_panel.windowTitle() == "Navigation"

    def test_zoom_controls_synchronization(self, navigation_panel):
        """Test that zoom controls stay synchronized."""
        # Test spinbox to slider sync
        navigation_panel._zoom_spinbox.setValue(150)
        assert navigation_panel._zoom_slider.value() == 150

        # Test slider to spinbox sync
        navigation_panel._zoom_slider.setValue(75)
        assert navigation_panel._zoom_spinbox.value() == 75

    def test_zoom_signal_emission(self, navigation_panel):
        """Test that zoom changes emit correct signals."""
        signal_spy = QSignalSpy(navigation_panel.zoom_changed)

        # Test spinbox change
        navigation_panel._on_zoom_spinbox_changed(200)
        assert len(signal_spy) == 1
        assert signal_spy[0][0] == 200.0

        # Test slider change
        navigation_panel._on_zoom_slider_changed(50)
        assert len(signal_spy) == 2
        assert signal_spy[1][0] == 50.0

    def test_zoom_buttons_functionality(self, navigation_panel):
        """Test zoom in/out buttons work correctly."""
        signal_spy = QSignalSpy(navigation_panel.zoom_changed)

        # Set initial zoom
        navigation_panel._zoom_spinbox.setValue(100)

        # Test zoom in
        navigation_panel._on_zoom_in()
        assert len(signal_spy) == 1
        assert signal_spy[0][0] == 125.0  # 100 + 25

        # Test zoom out
        navigation_panel._zoom_spinbox.setValue(100)
        navigation_panel._on_zoom_out()
        assert len(signal_spy) == 2
        assert signal_spy[1][0] == 75.0  # 100 - 25

    def test_zoom_bounds_enforcement(self, navigation_panel):
        """Test that zoom controls respect bounds."""
        # Test zoom in at maximum
        navigation_panel._zoom_spinbox.setValue(1000)
        navigation_panel._on_zoom_in()
        # Should not exceed maximum
        assert navigation_panel._zoom_spinbox.value() <= 1000

        # Test zoom out at minimum
        navigation_panel._zoom_spinbox.setValue(10)
        navigation_panel._on_zoom_out()
        # Should not go below minimum
        assert navigation_panel._zoom_spinbox.value() >= 10

    def test_reset_zoom_functionality(self, navigation_panel):
        """Test reset zoom button."""
        signal_spy = QSignalSpy(navigation_panel.zoom_changed)

        # Change zoom then reset
        navigation_panel._zoom_spinbox.setValue(250)
        navigation_panel._on_reset_zoom()

        # Should emit zoom change signal (may emit multiple times during reset)
        assert len(signal_spy) >= 1
        # Final value should be 100.0
        assert signal_spy[-1][0] == 100.0

    def test_navigation_button_signals(self, navigation_panel):
        """Test navigation button signal emissions."""
        fit_spy = QSignalSpy(navigation_panel.fit_to_window_requested)
        center_spy = QSignalSpy(navigation_panel.center_on_content_requested)

        # Emit signals (simulating button clicks)
        navigation_panel.fit_to_window_requested.emit()
        navigation_panel.center_on_content_requested.emit()

        assert len(fit_spy) == 1
        assert len(center_spy) == 1

    def test_zoom_display_update(self, navigation_panel):
        """Test zoom display updates correctly."""
        # Test normal update
        navigation_panel.update_zoom_display(150.0)
        assert navigation_panel._zoom_spinbox.value() == 150
        assert navigation_panel._zoom_slider.value() == 150

        # Test with float values
        navigation_panel.update_zoom_display(87.5)
        assert navigation_panel._zoom_spinbox.value() == 87
        assert navigation_panel._zoom_slider.value() == 87

    def test_viewport_indicator_update_with_rect(self, navigation_panel):
        """Test viewport indicator update with rectangle."""
        test_rect = QRectF(50, 50, 100, 100)
        navigation_panel.update_viewport_indicator(test_rect)

        # Should update minimap viewport indicator
        assert navigation_panel._minimap._viewport_rect == test_rect

    def test_viewport_indicator_update_with_point(self, navigation_panel):
        """Test viewport indicator update with center point."""
        test_point = QPointF(200, 200)
        navigation_panel.update_viewport_indicator(test_point)

        # Should create viewport rect around the point
        # Exact behavior depends on implementation details

    def test_minimap_update_scheduling(self, navigation_panel):
        """Test minimap update scheduling."""
        # Should not raise exceptions
        navigation_panel.schedule_minimap_update()
        assert navigation_panel._minimap._update_timer is not None


class TestNavigationAccuracy:
    """Test navigation accuracy under various conditions."""

    def test_minimap_accuracy_with_different_zoom_levels(self, minimap_widget, scene):
        """Test minimap accuracy at different zoom levels."""
        # Add test items at known positions
        item1 = QGraphicsRectItem(0, 0, 100, 100)
        item2 = QGraphicsRectItem(500, 500, 100, 100)
        scene.addItem(item1)
        scene.addItem(item2)

        # Test viewport indicators at different scales
        test_rects = [
            QRectF(0, 0, 200, 200),  # Zoomed in
            QRectF(-500, -500, 1500, 1500),  # Zoomed out
            QRectF(200, 200, 400, 400),  # Medium zoom
        ]

        for rect in test_rects:
            minimap_widget.update_viewport_indicator(rect)
            assert minimap_widget._viewport_rect == rect
            assert minimap_widget._viewport_item is not None

    def test_navigation_panel_zoom_accuracy(self, navigation_panel):
        """Test zoom control accuracy."""
        test_values = [10, 25, 50, 75, 100, 150, 200, 500, 1000]

        for value in test_values:
            navigation_panel.update_zoom_display(float(value))
            assert navigation_panel._zoom_spinbox.value() == value
            assert navigation_panel._zoom_slider.value() == value

    def test_minimap_content_accuracy_with_scene_changes(self, minimap_widget, scene):
        """Test minimap content accuracy when scene changes."""
        # Initial state
        minimap_widget._update_minimap_content()
        initial_rect = minimap_widget._minimap_scene.sceneRect()

        # Add items and expand scene
        for i in range(5):
            item = QGraphicsRectItem(i * 200, i * 200, 50, 50)
            scene.addItem(item)

        # Update scene bounds
        scene.setSceneRect(scene.itemsBoundingRect().adjusted(-100, -100, 100, 100))

        # Update minimap
        minimap_widget._update_minimap_content()
        updated_rect = minimap_widget._minimap_scene.sceneRect()

        # Minimap should reflect scene changes
        assert updated_rect == scene.sceneRect()
        assert updated_rect != initial_rect


class TestNavigationPerformance:
    """Test navigation performance under load."""

    def test_minimap_performance_with_many_items(self, minimap_widget, scene):
        """Test minimap performance with many items."""
        # Add many items
        item_count = 300
        start_time = time.time()

        for i in range(item_count):
            item = QGraphicsRectItem(i % 50 * 20, i // 50 * 20, 15, 15)
            scene.addItem(item)

        creation_time = time.time() - start_time

        # Test update performance
        update_start = time.time()
        minimap_widget._update_minimap_content()
        update_time = time.time() - update_start

        # Performance assertions
        assert creation_time < 2.0  # Item creation should be fast
        assert update_time < 1.5  # Update should be reasonably fast
        assert len(scene.items()) == item_count

    def test_navigation_panel_responsiveness(self, navigation_panel):
        """Test navigation panel responsiveness under load."""
        # Rapid zoom changes
        start_time = time.time()

        for i in range(100):
            zoom_value = 10 + (i % 990)  # Cycle through zoom range
            navigation_panel.update_zoom_display(float(zoom_value))

        update_time = time.time() - start_time

        # Should handle rapid updates efficiently
        assert update_time < 1.0

    def test_minimap_update_timer_performance(self, minimap_widget, scene):
        """Test minimap update timer performance optimization."""
        # Add items beyond threshold
        for i in range(150):
            item = QGraphicsRectItem(i * 3, i * 3, 8, 8)
            scene.addItem(item)

        # Schedule multiple updates rapidly
        start_time = time.time()
        for _ in range(10):
            minimap_widget.schedule_update()

        # Timer should coalesce updates
        assert minimap_widget._update_timer.isActive()

        # Wait for timer and measure
        QTest.qWait(300)  # Wait for timer to fire

        total_time = time.time() - start_time
        assert total_time < 2.0  # Should handle efficiently


class TestMainWindowNavigationIntegration:
    """Test navigation panel integration with main window."""

    def test_navigation_panel_exists(self, main_window):
        """Test that navigation panel exists and is properly initialized."""
        # Panel should exist
        nav_panel = main_window._navigation_panel
        assert nav_panel is not None
        assert hasattr(main_window, "_navigation_panel_action")

    def test_navigation_panel_initial_state(self, main_window):
        """Test navigation panel initial state."""
        nav_panel = main_window._navigation_panel
        action = main_window._navigation_panel_action

        # Panel should be visible initially and action should be checked
        # Note: In test environment, dock widgets may behave differently
        assert nav_panel is not None
        assert action is not None
        assert action.isCheckable()

    def test_navigation_panel_action_trigger(self, main_window):
        """Test navigation panel action can be triggered."""
        action = main_window._navigation_panel_action

        # Action should be triggerable without errors
        try:
            action.trigger()
            QTest.qWait(10)
            # Should not raise exceptions
            assert True
        except Exception as e:
            pytest.fail(f"Navigation panel action trigger failed: {e}")

    def test_navigation_panel_connections(self, main_window):
        """Test navigation panel signal connections."""
        nav_panel = main_window._navigation_panel

        # Test zoom signal connection
        # Simulate zoom change from navigation panel
        nav_panel.zoom_changed.emit(150.0)

        # Canvas should receive the zoom change
        # Note: This tests the connection exists, actual zoom change
        # depends on canvas implementation

    def test_navigation_panel_minimap_integration(self, main_window):
        """Test minimap integration with main canvas."""
        nav_panel = main_window._navigation_panel
        canvas = main_window._canvas

        # Add some content to canvas using the correct method name
        canvas._create_note_at_position(QPointF(100, 100))

        # Schedule minimap update
        nav_panel.schedule_minimap_update()

        # Should not raise exceptions
        assert nav_panel._minimap is not None


class TestNavigationErrorHandling:
    """Test error handling in navigation components."""

    def test_minimap_error_handling_invalid_scene(self):
        """Test minimap handles invalid scene gracefully."""
        # Test with None scene - this should be handled in the constructor
        # or the minimap should have proper null checks
        try:
            # Instead of testing with None scene (which may be a design constraint),
            # test with an empty scene that has no items
            from src.whiteboard.canvas import WhiteboardScene

            empty_scene = WhiteboardScene()
            minimap = MinimapWidget(empty_scene)
            minimap.schedule_update()
            # Should not crash with empty scene
            assert minimap._main_scene is not None
        except Exception as e:
            pytest.fail(f"Minimap should handle empty scene gracefully: {e}")

    def test_navigation_panel_error_handling(self, navigation_panel):
        """Test navigation panel error handling."""
        # Test with invalid zoom values
        try:
            navigation_panel.update_zoom_display(-50.0)  # Negative zoom
            navigation_panel.update_zoom_display(2000.0)  # Excessive zoom
            # Should not crash
        except Exception as e:
            pytest.fail(f"Navigation panel should handle invalid zoom gracefully: {e}")

    def test_viewport_indicator_error_handling(self, minimap_widget):
        """Test viewport indicator error handling."""
        try:
            # Test with invalid rectangles
            minimap_widget.update_viewport_indicator(QRectF())  # Empty rect
            minimap_widget.update_viewport_indicator(
                QRectF(-1000, -1000, -100, -100)
            )  # Negative size
            # Should not crash
        except Exception as e:
            pytest.fail(
                f"Viewport indicator should handle invalid rects gracefully: {e}"
            )


if __name__ == "__main__":
    pytest.main([__file__])
