import shiboken6
from PySide6.QtWidgets import QPushButton, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PySide6.QtCore import Signal, QPropertyAnimation, QEasingCurve, QRect, Qt, QParallelAnimationGroup, QSize
from PySide6.QtGui import QColor

from app_constance.styles import get_theme_palette

class ToggleButton(QPushButton):
    actuated = Signal(bool)
    

    def __init__(self, text=None, parent=None):
        super().__init__(parent)
        
        self.activated = False
        
        self.setupAnimations()
        
        self.setupStyle()
        
        self.clicked.connect(self.onActuate)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if text and text.strip():
            self.setText(text)
        
        self.updateAccessibility()
        self.updateStyle()
        
        self.setMinimumSize(100, 35)
        
    def setupAnimations(self):
        self.animationGroup = QParallelAnimationGroup(self)
        
        self.opacityEffect = QGraphicsOpacityEffect()
        
        self.opacityAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.opacityAnimation.setDuration(200)
        self.opacityAnimation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.sizeAnimation = QPropertyAnimation(self, b"minimumSize")
        self.sizeAnimation.setDuration(250)
        self.sizeAnimation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.animationGroup.addAnimation(self.opacityAnimation)
        self.animationGroup.addAnimation(self.sizeAnimation)
        
        self.shadowEffect = QGraphicsDropShadowEffect()
        self.shadowEffect.setBlurRadius(8)
        self.shadowEffect.setOffset(0, 4)
        self.shadowEffect.setColor(self._shadow_color())
        self.shadowEffect.setEnabled(False)
        
        self.shadowAnimation = QPropertyAnimation(self.shadowEffect, b"blurRadius")
        self.shadowAnimation.setDuration(200)
        self.shadowAnimation.setEasingCurve(QEasingCurve.Type.OutQuad)

    def _ensure_opacity_effect(self):
        # setGraphicsEffect() deletes a widget's previously-installed effect
        # when swapping to a new one, so opacityEffect/shadowEffect become
        # dangling C++ objects each time they're swapped out for the other.
        if not shiboken6.isValid(self.opacityEffect):
            self.opacityEffect = QGraphicsOpacityEffect()
            self.opacityAnimation.setTargetObject(self.opacityEffect)

    def _ensure_shadow_effect(self):
        if not shiboken6.isValid(self.shadowEffect):
            self.shadowEffect = QGraphicsDropShadowEffect()
            self.shadowEffect.setBlurRadius(8)
            self.shadowEffect.setOffset(0, 4)
            self.shadowEffect.setColor(self._shadow_color())
            self.shadowEffect.setEnabled(False)
            self.shadowAnimation.setTargetObject(self.shadowEffect)

    @staticmethod
    def _shadow_color():
        color = QColor(get_theme_palette().COLOR_ACCENT_4)
        color.setAlpha(76)
        return color

    def setupStyle(self):
        palette = get_theme_palette()
        self.base_style = f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {palette.COLOR_ACCENT_3};
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                color: {palette.COLOR_TEXT_1};
                text-align: center;
            }}
            
            QPushButton:hover {{
                border-color: {palette.COLOR_ACCENT_4};
                background-color: {palette.COLOR_ACCENT_1};
            }}
            
            QPushButton:pressed {{
                background-color: {palette.COLOR_ACCENT_2};
            }}
        """
        
        self.activated_style = f"""
            QPushButton {{
                background-color: {palette.COLOR_ACCENT_3};
                border: 2px solid {palette.COLOR_ACCENT_4};
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                color: {palette.COLOR_TEXT_1};
                text-align: center;
            }}
            
            QPushButton:hover {{
                background-color: {palette.COLOR_ACCENT_4};
                border-color: {palette.COLOR_ACCENT_5};
            }}
            
            QPushButton:pressed {{
                background-color: {palette.COLOR_ACCENT_2};
            }}
        """

    def apply_theme_styles(self):
        self.setupStyle()
        self._ensure_shadow_effect()
        self.shadowEffect.setColor(self._shadow_color())
        self.updateStyle()
        
    def updateStyle(self):
        if self.activated:
            self.setStyleSheet(self.activated_style)
            self.setProperty("toggled", True)
        else:
            self.setStyleSheet(self.base_style)
            self.setProperty("toggled", False)
        
        self.style().unpolish(self)
        self.style().polish(self)
        
    def updateAccessibility(self):
        if self.activated:
            self.setAccessibleDescription(_("Toggle button activated - Press to deactivate"))
            self.setAccessibleName(_("{label} - Active").format(label=self.text()))
        else:
            self.setAccessibleDescription(_("Toggle button not activated - Press to activate"))
            self.setAccessibleName(_("{label} - Inactive").format(label=self.text()))
            
    def setActuated(self, state):
        if isinstance(state, bool) and state != self.activated:
            self.activated = state
            self.actuatedChange()
            self.updateStyle()
            self.updateAccessibility()
            self.actuated.emit(self.activated)
        elif not isinstance(state, bool):
            raise TypeError("State must be boolean")
            
    def isActuated(self):
        return self.activated
        
    def onActuate(self):
        self.activated = not self.activated
        self.actuatedChange()
        self.updateStyle()
        self.updateAccessibility()
        self.actuated.emit(self.activated)
        
    def actuatedChange(self):
        if self.animationGroup.state() == QParallelAnimationGroup.State.Running:
            self.animationGroup.stop()

        self._ensure_opacity_effect()
        self.opacityAnimation.setStartValue(1.0)
        self.opacityAnimation.setKeyValueAt(0.5, 0.7)
        self.opacityAnimation.setEndValue(1.0)
        
        current_size = self.minimumSize()
        
        if self.activated:
            target_size = self.size() if self.size().isValid() else current_size
            target_size.setWidth(max(target_size.width(), current_size.width() + 10))
            target_size.setHeight(max(target_size.height(), current_size.height() + 2))
        else:
            target_size = current_size
            
        self.sizeAnimation.setStartValue(current_size)
        self.sizeAnimation.setEndValue(target_size)
        
        self.animationGroup.start()
        
    def enterEvent(self, event):
        super().enterEvent(event)
        if self.activated:
            self._ensure_shadow_effect()
            current_effect = self.graphicsEffect()
            if current_effect != self.shadowEffect:
                self.setGraphicsEffect(self.shadowEffect)
            self.shadowEffect.setEnabled(True)
            self.shadowAnimation.stop()
            self.shadowAnimation.setStartValue(self.shadowEffect.blurRadius())
            self.shadowAnimation.setEndValue(12)
            self.shadowAnimation.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._ensure_shadow_effect()
        if self.shadowEffect.isEnabled():
            self.shadowAnimation.stop()
            self.shadowAnimation.setStartValue(self.shadowEffect.blurRadius())
            self.shadowAnimation.setEndValue(0)
            self.shadowAnimation.finished.connect(self._restoreOpacityEffect)
            self.shadowAnimation.start()

    def _restoreOpacityEffect(self):
        self._ensure_shadow_effect()
        self.shadowEffect.setEnabled(False)
        self._ensure_opacity_effect()
        self.setGraphicsEffect(self.opacityEffect)
        try:
            self.shadowAnimation.finished.disconnect(self._restoreOpacityEffect)
        except:
            pass
            
    def sizeHint(self):
        hint = super().sizeHint()
        hint.setWidth(max(hint.width(), 100))
        hint.setHeight(max(hint.height(), 35))
        return hint
        
    def setText(self, text):
        super().setText(text)
        self.updateAccessibility()
        
    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        if not enabled and hasattr(self, 'animationGroup'):
            self.animationGroup.stop()
            
    def __del__(self):
        if hasattr(self, 'animationGroup') and shiboken6.isValid(self.animationGroup):
            self.animationGroup.stop()