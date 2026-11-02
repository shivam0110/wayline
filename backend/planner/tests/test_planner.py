from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from planner.providers import truck_route
from planner.risk import LEVELS, classify, recommend, summarize
from planner.routing import MILE, corridor_grid, sample_route
from planner.weather import at_time


class PlannerTests(SimpleTestCase):
    def test_backend_only_deployment_has_a_working_root(self):
        with TemporaryDirectory() as folder, override_settings(BASE_DIR=Path(folder) / 'backend'):
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['health'], '/api/health')
            self.assertEqual(self.client.get('/unknown').status_code, 404)

    @override_settings(CORS_ALLOWED_ORIGINS=['https://wayline.vercel.app'])
    def test_separate_frontend_can_call_api(self):
        response = self.client.options('/api/plan', HTTP_ORIGIN='https://wayline.vercel.app', HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST', HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], 'https://wayline.vercel.app')
        self.assertIn('POST', response['Access-Control-Allow-Methods'])
        self.assertIn('content-type', response['Access-Control-Allow-Headers'])
        self.assertNotIn('Access-Control-Allow-Origin', self.client.get('/api/health', HTTP_ORIGIN='https://another-site.example'))

    def test_weather_boundaries(self):
        cases = {
            'wind': [(24.999, 0), (25, 1), (34.999, 1), (35, 2), (45, 3), (54.999, 3), (55, 4)],
            'rain': [(.0999, 0), (.1, 1), (.25, 2), (.5, 3), (1, 3), (1.0001, 4)],
            'snow': [(.4999, 0), (.5, 1), (1, 2), (2, 3), (3, 3), (3.0001, 4)],
        }
        for condition, values in cases.items():
            for value, level in values:
                with self.subTest(condition=condition, value=value):
                    weather = dict(wind=0, rain=0, snow=0)
                    weather[condition] = value
                    self.assertEqual(classify(weather, 0)['level'], level)

    def test_strict_load_boundaries_and_combined_hazards(self):
        for wind, load, level in [(45, 30000, 3), (45, 30001, 4), (35, 40000, 2), (35, 40001, 3), (55, 0, 4)]:
            with self.subTest(wind=wind, load=load):
                self.assertEqual(classify(dict(wind=wind, rain=0, snow=0), load)['level'], level)
        self.assertEqual(classify(dict(wind=35, rain=1.01, snow=0), 40001)['level'], 4)

    def test_missing_weather_is_unknown(self):
        for weather in [None, dict(wind=None, rain=0, snow=0), dict(wind=float('nan'), rain=0, snow=0)]:
            self.assertIsNone(classify(weather, 0)['level'])
        result = summarize([dict(miles=7, risk=None), dict(miles=10, risk=0)])
        self.assertFalse(result['eligible'])
        self.assertIsNone(result['average_risk'])
        self.assertEqual(result['unknown_miles'], 7)

    def test_distance_weighted_average_and_blocked_routes(self):
        result = summarize([dict(miles=25, risk=0), dict(miles=25, risk=2), dict(miles=7, risk=3)])
        self.assertAlmostEqual(result['average_risk'], 71 / 57)
        self.assertEqual(sum(result['risk_miles'].values()), 57)
        self.assertFalse(summarize([dict(miles=1, risk=4)])['eligible'])

    def test_lexicographic_recommendation(self):
        def route(id, severe, high, avg, seconds, eligible=True):
            return dict(id=id, risk_miles={'Severe': severe, 'High': high}, average_risk=avg, duration_seconds=seconds, eligible=eligible)
        a = route('a', 0, 10, 2, 900)
        b = route('b', 1, 0, .1, 100)
        self.assertEqual(recommend([b, a]), 'a')
        self.assertEqual(recommend([a, route('c', 0, 9, 3, 1000)]), 'c')
        self.assertEqual(recommend([a, route('c', 0, 10, 1, 1000)]), 'c')
        self.assertEqual(recommend([a, route('c', 0, 10, 2, 800)]), 'c')
        self.assertIsNone(recommend([route('blocked', 0, 0, 0, 1, False)]))

    def test_sampling_retains_endpoints_and_partial_segment(self):
        route = dict(geometry=[[0, 0], [0, 1], [1, 1]], distance_meters=57 * MILE, duration_seconds=1000, vertex_seconds=[0, 800, 1000])
        points, segments = sample_route(route, 25)
        self.assertEqual([p['mile'] for p in points], [0, 25, 50, 57])
        self.assertEqual(points[0]['coordinate'], [0, 0])
        self.assertEqual(points[-1]['coordinate'], [1, 1])
        self.assertEqual(segments[-1]['miles'], 7)
        self.assertGreater(points[1]['elapsed_seconds'], 500)
        self.assertAlmostEqual(sum(s['miles'] for s in segments), 57)
        route['distance_meters'] = 50 * MILE
        self.assertEqual([p['mile'] for p in sample_route(route, 25)[0]], [0, 25, 50])

    def test_forecast_intervals_units_and_wind_interpolation(self):
        hourly = dict(time=[0, 3600, 7200], wind_speed_10m=[10, 20, 30], rain=[0, 12.7, 25.4], showers=[0, 12.7, 0], snowfall=[0, 2.54, 0])
        weather = at_time(hourly, 1800)
        self.assertEqual(weather['wind'], 15)
        self.assertEqual(weather['rain'], 1)
        self.assertEqual(weather['snow'], 1)
        self.assertIsNotNone(at_time(hourly, 7200))
        self.assertIsNone(at_time(hourly, 7201))
        self.assertIsNone(at_time(hourly, -1))
        self.assertIsNone(at_time(None, 0))

    def test_corridor_is_bounded_2d_grid(self):
        cells, resolution = corridor_grid([[[-87.6, 41.8], [-83.0, 42.3]]])
        self.assertTrue(1 < len(cells) <= 120)
        self.assertGreater(resolution, 0)
        self.assertGreater(len({c['coordinate'][1] for c in cells}), 1)
        self.assertTrue(all(len(c['polygon']) == 5 for c in cells))

    def test_reject_bad_inputs_before_external_requests(self):
        base = dict(origin=[0, 0], destination=[1, 1], departure=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(), load_lb=35000, interval_miles=25)
        for field, value in [('origin', [200, 0]), ('load_lb', -1), ('load_lb', True), ('interval_miles', 13), ('departure', '2020-01-01T00:00:00Z'), ('departure', '2030-01-01T00:00:00'), ('destination', [0, 0])]:
            with self.subTest(field=field, value=value), patch('planner.providers.routes') as provider:
                response = self.client.post('/api/plan', {**base, field: value}, content_type='application/json')
                self.assertEqual(response.status_code, 400)
                provider.assert_not_called()
        self.assertEqual(self.client.get('/api/plan').status_code, 405)
        self.assertEqual(self.client.post('/api/plan', '[]', content_type='application/json').status_code, 400)

    @patch('planner.providers.forecasts')
    @patch('planner.providers.routes')
    def test_plan_api_and_timezone_conversion(self, routing, weather):
        route = dict(geometry=[[0, 0], [.5, .5], [1, 1]], distance_meters=57 * MILE, duration_seconds=3600)
        routing.return_value = [route], 'Test fixture', []
        departure = datetime.now(timezone(timedelta(hours=5, minutes=30))) + timedelta(hours=1)
        start = int(departure.timestamp() // 3600 * 3600)
        hourly = dict(time=[start + i * 3600 for i in range(4)], wind_speed_10m=[0] * 4, rain=[0] * 4, showers=[0] * 4, snowfall=[0] * 4)
        weather.side_effect = lambda coordinates: [hourly for _ in coordinates]
        response = self.client.post('/api/plan', dict(origin=[0, 0], destination=[1, 1], departure=departure.isoformat(), load_lb=35000, interval_miles=25), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['departure'].endswith('+00:00'))
        self.assertEqual(data['recommendation_id'], 'route-1')
        self.assertEqual(len(data['routes'][0]['checkpoints']), 4)
        self.assertAlmostEqual(sum(data['routes'][0]['risk_miles'].values()), 57)

    @patch('planner.providers.forecasts', side_effect=lambda coordinates: [None] * len(coordinates))
    def test_corridor_includes_48h_and_explicit_missing_cells(self, weather):
        response = self.client.post('/api/corridor-weather', {'routes': [[[0, 0], [1, 1]]]}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['timestamps']), 49)
        self.assertEqual((datetime.fromisoformat(data['timestamps'][-1]) - datetime.fromisoformat(data['timestamps'][0])).total_seconds(), 48 * 3600)
        self.assertEqual(data['unavailable_cells'], len(data['cells']))
        self.assertEqual(data['cells'][0]['values'], [None] * 49)
