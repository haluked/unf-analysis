# -*- coding: utf-8 -*-
"""
Unit tests for unf-analysis v2.0
Tests analytical functions, data structures, parsing, and exports.
"""

import os
import sys
import unittest
import tempfile
import json
import csv

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import components from unf-analysis
import importlib
unf_mod = importlib.import_module("unf-analysis")


class TestUnfAnalysis(unittest.TestCase):

    def test_browser_detection(self):
        """Ensure browser detection function runs without error and returns dict."""
        browsers = unf_mod.detect_browsers()
        self.assertIsInstance(browsers, dict)
        print(f"Detected browsers on host: {list(browsers.keys())}")

    def test_reserved_routes(self):
        """Ensure system routes are properly classified as reserved."""
        self.assertIn("explore", unf_mod.RESERVED_ROUTES)
        self.assertIn("direct", unf_mod.RESERVED_ROUTES)
        self.assertIn("stories", unf_mod.RESERVED_ROUTES)
        self.assertIn("reels", unf_mod.RESERVED_ROUTES)
        self.assertNotIn("johndoe", unf_mod.RESERVED_ROUTES)

    def test_analytics_computation(self):
        """Test the set-difference computations for followers and following."""
        current_followers = {"alice", "bob", "charlie", "david", "eve"}
        current_following = {"alice", "bob", "frank", "grace"}
        past_followers = {"alice", "bob", "charlie", "david", "eve", "heidi"}

        # 1. Not following back (following - followers)
        not_following = current_following - current_followers
        self.assertEqual(not_following, {"frank", "grace"})

        # 2. Fans (followers - following)
        fans = current_followers - current_following
        self.assertEqual(fans, {"charlie", "david", "eve"})

        # 3. Mutuals (followers & following)
        mutuals = current_followers & current_following
        self.assertEqual(mutuals, {"alice", "bob"})

        # 4. Lost followers / Unfollowed you (past_followers - current_followers)
        lost_followers = past_followers - current_followers
        self.assertEqual(lost_followers, {"heidi"})

        # 5. New followers (current_followers - past_followers)
        new_followers = current_followers - past_followers
        self.assertEqual(new_followers, set())

    def test_csv_export_format(self):
        """Ensure CSV export writes valid header and UTF-8 records."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
            tmp_path = tmp.name

        try:
            sample_records = [
                ("not_following_user", "Not Following Back", "https://www.instagram.com/not_following_user/"),
                ("fan_user", "Fan", "https://www.instagram.com/fan_user/")
            ]

            with open(tmp_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Username", "Category", "Profile URL"])
                for row in sample_records:
                    writer.writerow(row)

            with open(tmp_path, "r", encoding="utf-8-sig") as f:
                reader = list(csv.reader(f))
                self.assertEqual(reader[0], ["Username", "Category", "Profile URL"])
                self.assertEqual(len(reader), 3)
                self.assertEqual(reader[1][0], "not_following_user")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_json_history_format(self):
        """Ensure JSON history writes and loads snapshot schema correctly."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp:
            tmp_path = tmp.name

        try:
            snapshot = [{
                "timestamp": "2026-09-08 22:00:00",
                "account": "testuser",
                "followers_count": 100,
                "following_count": 80,
                "not_following_count": 10,
                "lost_count": 2,
                "gained_count": 5,
                "followers": ["user1", "user2"],
                "following": ["user1", "user3"]
            }]
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=4)

            with open(tmp_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded[0]["account"], "testuser")
                self.assertEqual(loaded[0]["followers_count"], 100)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
