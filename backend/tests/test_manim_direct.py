from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#1A1A2E"

        title = Text("Pythagorean Theorem", font_size=36, color=WHITE, weight=BOLD)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=0.8)

        s = 0.55
        A = np.array([0, 0, 0])
        B = np.array([3 * s, 0, 0])
        C = np.array([0, 4 * s, 0])

        triangle = Polygon(A, B, C, color=WHITE, fill_opacity=0.15, stroke_width=3)
        angle_mark = Square(side_length=0.25, color=WHITE, stroke_width=2)
        angle_mark.move_to(A + np.array([0.125, 0.125, 0]))

        def make_sq(p1, p2, col, flip=False):
            vec = p2 - p1
            perp = np.array([-vec[1], vec[0], 0])
            if flip:
                perp = -perp
            return Polygon(p1, p2, p2 + perp, p1 + perp,
                           color=col, fill_opacity=0.3, stroke_width=2)

        sq_a = make_sq(A, B, YELLOW, flip=True)
        sq_b = make_sq(A, C, GREEN)
        sq_c = make_sq(B, C, RED, flip=True)

        geo = VGroup(triangle, angle_mark, sq_a, sq_b, sq_c)
        geo.move_to(LEFT * 2.5 + DOWN * 0.3)

        v = triangle.get_vertices()
        la = Text("a", font_size=26, color=YELLOW, weight=BOLD)
        lb = Text("b", font_size=26, color=GREEN, weight=BOLD)
        lc = Text("c", font_size=26, color=RED, weight=BOLD)
        la.move_to((v[0] + v[1]) / 2 + DOWN * 0.25)
        lb.move_to((v[0] + v[2]) / 2 + LEFT * 0.3)
        lc.move_to((v[1] + v[2]) / 2 + np.array([0.2, 0.2, 0]))

        self.play(Create(triangle), Create(angle_mark), run_time=1)
        self.play(Write(la), Write(lb), Write(lc), run_time=0.8)

        self.play(LaggedStart(
            Create(sq_a), Create(sq_b), Create(sq_c),
            lag_ratio=0.3,
        ), run_time=2)

        la2 = Text("a²", font_size=22, color=YELLOW).move_to(sq_a.get_center())
        lb2 = Text("b²", font_size=22, color=GREEN).move_to(sq_b.get_center())
        lc2 = Text("c²", font_size=22, color=RED).move_to(sq_c.get_center())
        self.play(Write(la2), Write(lb2), Write(lc2), run_time=0.8)

        eq = Text("a² + b² = c²", font_size=48, color=WHITE, weight=BOLD)
        eq.move_to(RIGHT * 3)
        box = SurroundingRectangle(eq, color=GOLD, buff=0.2, corner_radius=0.1, stroke_width=2.5)

        self.play(Write(eq), run_time=1)
        self.play(Create(box), run_time=0.5)
        self.play(Indicate(eq, color=YELLOW), run_time=0.8)
        self.wait(1)
