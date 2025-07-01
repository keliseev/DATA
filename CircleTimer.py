from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.label import Label

class CircleTimer(Widget):
    progress = NumericProperty(1.0)
    time_text = StringProperty("00:00:00")
    def __init__(self, **kwargs):
      super().__init__(**kwargs)
      with self.canvas:
          # Создаем графику один раз и запоминаем объекты
          self.shadow_color = Color(0, 0, 0, 0.15)
          self.shadow_ellipse = Ellipse()

          self.bg_color = Color(0.3, 0.3, 0.3, 0.3)
          self.bg_ellipse = Ellipse()

          self.progress_color = Color(0.2, 0.6, 0.2, 1)
          self.progress_line = Line(width=6, cap='round')

      # Создаем лейбл
      self.time_label = Label(
          text=self.time_text,
          font_name="Roboto",
          font_size='40sp',
          color=(1, 1, 1, 1),
          size_hint=(None, None),
          halign="center",
          valign="middle",
      )
      with self.time_label.canvas.before:
          Color(0, 0, 0, 0)
          self.bg_rect = Rectangle(pos=self.time_label.pos, size=self.time_label.size)
      self.add_widget(self.time_label)

      # Связываем обновления
      self.bind(pos=self.update_canvas, size=self.update_canvas, progress=self.update_canvas, time_text=self.update_text)
      self.time_label.bind(pos=self.update_bg_rect, size=self.update_bg_rect)

      self.update_label_pos()
      self.update_canvas()

    def update_canvas(self, *args):
      radius_shadow = min(self.size) / 2 - 5
      cx, cy = self.center_x, self.center_y

      self.shadow_ellipse.pos = (cx - radius_shadow, cy - radius_shadow)
      self.shadow_ellipse.size = (radius_shadow * 2, radius_shadow * 2)

      radius_bg = radius_shadow - 10
      self.bg_ellipse.pos = (cx - radius_bg, cy - radius_bg)
      self.bg_ellipse.size = (radius_bg * 2, radius_bg * 2)

      self.progress_line.circle = (cx, cy, radius_bg, 0, 360 * self.progress)

    def update_bg_rect(self, *args):
      self.bg_rect.pos = self.time_label.pos
      self.bg_rect.size = self.time_label.size

    def update_text(self, *args):
      self.time_label.text = self.time_text
      self.update_label_pos()

    def update_label_pos(self):
      label_width = self.width * 0.8
      label_height = 50
      self.time_label.size = (label_width, label_height)
      self.time_label.text_size = self.time_label.size
      self.time_label.pos = (
          self.center_x - label_width / 2,
          self.center_y - label_height / 2,
      )