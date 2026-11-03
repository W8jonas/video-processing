from collections import Counter
from copy import deepcopy
from math import isclose
import unittest

from hand_math.cube import project
from hand_math.drawing import (DrawingCommands, FingerDrawing, TIPS, active_tips,
                               build_drawing, input_from_hands)


def hands_with_counts(left_count, right_count):
    result = []
    names = {1: ('indicador',), 2: ('polegar', 'indicador'),
             3: ('polegar', 'indicador', 'medio'), 0: (),
             5: tuple(name for name, _ in TIPS)}
    for side, (x, count) in enumerate(((.25, left_count), (.75, right_count))):
        points = [(x, .7, 0)] * 21
        direction = 1 if side == 0 else -1
        points[4] = (x - direction * .15, .68, 0)
        points[8] = (x, .25, 0)
        points[12] = (x + direction * .14, .28, 0)
        points[16] = (x + direction * .18, .35, 0)
        points[20] = (x + direction * .22, .42, 0)
        result.append(dict(points=points, fingers={name: name in names[count] for name, _ in TIPS}))
    return result


class DrawingGeometryTests(unittest.TestCase):
    def test_all_requested_counts_and_swapped_hands_build_expected_shapes(self):
        for counts, kind, vertices, edges, faces in (
                ((2, 1), 'triangle', 3, 3, 1),
                ((2, 2), 'rectangle', 4, 4, 1),
                ((3, 1), 'pyramid', 4, 6, 4),
                ((3, 3), 'cube', 8, 12, 6)):
            for actual_counts in (counts, tuple(reversed(counts))):
                hands = hands_with_counts(*actual_counts)
                source = input_from_hands(list(reversed(hands)), 1000, 600)
                drawing = build_drawing(source)
                self.assertIsNotNone(drawing, (kind, actual_counts))
                self.assertEqual(source.kind, kind)
                self.assertEqual((len(drawing.mesh.vertices), len(drawing.mesh.edges), len(drawing.mesh.faces)),
                                 (vertices, edges, faces))

    def test_measured_corners_reproject_exactly_onto_every_fingertip(self):
        for counts in ((2, 1), (2, 2), (3, 1), (3, 3)):
            drawing = build_drawing(input_from_hands(hands_with_counts(*counts), 1000, 600))
            screen = project(drawing.mesh.vertices, drawing.pose)
            bound = set()
            for projected, binding in zip(screen, drawing.bindings):
                if binding is not None:
                    bound.add(binding.identity)
                    self.assertTrue(all(isclose(a, b, abs_tol=1e-8) for a, b in zip(projected, binding.point)))
            self.assertEqual(bound, {tip.identity for tip in drawing.source.tips})
            self.assertEqual(sum(binding is None for binding in drawing.bindings), 2 if counts == (3, 3) else 0)

    def test_moving_one_tip_moves_geometry_not_a_stock_pose(self):
        hands = hands_with_counts(3, 1)
        original = build_drawing(input_from_hands(hands, 1000, 600))
        hands[1]['points'][8] = (.85, .35, 0)
        moved = build_drawing(input_from_hands(hands, 1000, 600))
        self.assertNotEqual(original.screen, moved.screen)
        self.assertIn((850, 210), moved.screen)
        self.assertEqual(original.screen[:3], moved.screen[:3])

    def test_cube_and_pyramid_have_closed_topology(self):
        for counts in ((3, 1), (3, 3)):
            mesh = build_drawing(input_from_hands(hands_with_counts(*counts), 1000, 600)).mesh
            incidence = Counter(tuple(sorted((face[i], face[(i + 1) % len(face)])))
                                for face in mesh.faces for i in range(len(face)))
            self.assertTrue(all(count == 2 for count in incidence.values()))
            self.assertEqual(len(mesh.vertices) - len(mesh.edges) + len(mesh.faces), 2)

    def test_unsupported_missing_collinear_and_nonfinite_inputs_are_rejected(self):
        self.assertIsNone(input_from_hands(hands_with_counts(3, 2), 1000, 600))
        self.assertIsNone(input_from_hands(hands_with_counts(1, 1)[:1], 1000, 600))
        for counts in ((2, 2), (3, 1), (3, 3)):
            hands = hands_with_counts(*counts)
            for hand in hands:
                hand['points'] = [(x, .5, z) for x, y, z in hand['points']]
            self.assertIsNone(build_drawing(input_from_hands(hands, 1000, 600)))
        hands = hands_with_counts(3, 1)
        hands[1]['points'][8] = (float('nan'), .3, 0)
        self.assertIsNone(build_drawing(input_from_hands(hands, 1000, 600)))

    def test_active_fingers_need_not_be_a_fixed_thumb_index_subset(self):
        hands = hands_with_counts(2, 1)
        hands[0]['fingers']['polegar'] = False
        hands[0]['fingers']['medio'] = True
        counts, tips = active_tips(hands, 1000, 600)
        self.assertEqual(counts, (2, 1))
        self.assertEqual([tip.finger for tip in tips if tip.side == 0], ['indicador', 'medio'])

    def test_fixed_profiles_use_named_landmarks_even_when_extension_count_is_wrong(self):
        hands = hands_with_counts(0, 0)
        for profile, expected in (('triangle', (2, 1)), ('rectangle', (2, 2)),
                                  ('pyramid', (3, 1)), ('cube', (3, 3))):
            source = input_from_hands(hands, 1000, 600, profile=profile)
            self.assertEqual(source.counts, expected)
            self.assertIsNotNone(build_drawing(source))
        controller = FingerDrawing(profile='cube')
        controller.update(hands, 1000, 600, 0)
        self.assertIsNotNone(controller.update(hands, 1000, 600, .4))


class DrawingStateTests(unittest.TestCase):
    def test_diagnostic_distinguishes_tracking_counts_and_geometry_failures(self):
        controller = FingerDrawing()
        controller.update([], 1000, 600, 0)
        self.assertEqual(controller.status, 'two_hands')
        controller.update(hands_with_counts(3, 2), 1000, 600, .1)
        self.assertEqual(controller.status, 'unsupported_counts')
        hands = hands_with_counts(2, 2)
        for hand in hands:
            hand['points'] = [(x, .5, z) for x, y, z in hand['points']]
        controller.update(hands, 1000, 600, .2)
        self.assertEqual(controller.status, 'degenerate_geometry')

    def test_new_shape_requires_stability_and_tracking_loss_clears_state(self):
        controller = FingerDrawing()
        hands = hands_with_counts(2, 2)
        self.assertIsNone(controller.update(hands, 1000, 600, 0))
        self.assertIsNone(controller.update(hands, 1000, 600, .2))
        self.assertIsNotNone(controller.update(hands, 1000, 600, .4))
        self.assertIsNone(controller.update(hands_with_counts(2, 1), 1000, 600, .5))
        self.assertIsNone(controller.update([], 1000, 600, .6))
        self.assertIsNone(controller.update(hands, 1000, 600, .7))

    def test_vertex_smoothing_preserves_identity_and_projection(self):
        controller = FingerDrawing()
        hands = hands_with_counts(2, 2)
        controller.update(hands, 1000, 600, 0)
        before = controller.update(hands, 1000, 600, .4)
        moved = deepcopy(hands)
        x, y, z = moved[0]['points'][8]
        moved[0]['points'][8] = (x + .05, y, z)
        after = controller.update(moved, 1000, 600, .45)
        old_tip = next(tip for tip in before.source.tips if tip.identity == (0, 'indicador'))
        new_tip = next(tip for tip in after.source.tips if tip.identity == old_tip.identity)
        self.assertGreater(new_tip.point[0], old_tip.point[0])
        self.assertLess(new_tip.point[0], (x + .05) * 1000)
        for screen, binding in zip(project(after.mesh.vertices, after.pose), after.bindings):
            self.assertAlmostEqual(screen[0], binding.point[0])

    def test_freeze_and_style_commands_do_not_conflict_with_drawing_counts(self):
        for command_counts, expected in (((0, 0), 'style'), ((5, 5), 'freeze')):
            commands = DrawingCommands()
            self.assertIsNone(commands.update(command_counts, 0))
            commands.update((3, 3), .1)
            commands.update((3, 3), .4)
            self.assertIsNone(commands.update(command_counts, .5))
            self.assertEqual(commands.update(command_counts, 1.4), expected)
            self.assertIsNone(commands.update(command_counts, 2))
            commands.update((), 2.1)
            self.assertIsNone(commands.update(command_counts, 3))
