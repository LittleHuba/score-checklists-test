# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

"""Tests for post_checklists.py."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from post_checklists import main


def _make_file(filename):
    f = MagicMock()
    f.filename = filename
    return f


SAMPLE_CHECKLISTS = [
    {
        "id": "api-review",
        "name": "API Review",
        "paths": ["src/api/*.py"],
        "checklist": "- [ ] Reviewed",
    },
]


class TestPostChecklistsMain:
    """Integration-level tests for the main() entry point."""

    @patch("post_checklists.set_commit_status")
    @patch("post_checklists.load_checklists", return_value=SAMPLE_CHECKLISTS)
    @patch("post_checklists.get_repo_and_pr")
    @patch("post_checklists.get_github_client")
    def test_no_relevant_checklists_sets_success(
        self, mock_gh, mock_repo_pr, mock_load, mock_status
    ):
        repo = MagicMock()
        pr = MagicMock()
        pr.head.sha = "abc123"
        pr.get_files.return_value = [_make_file("unrelated/file.txt")]
        mock_repo_pr.return_value = (repo, pr)

        main()

        mock_status.assert_called_once_with(
            repo, "abc123", "success", "No checklists applicable"
        )

    @patch("post_checklists.set_commit_status")
    @patch("post_checklists.find_existing_checklist_comments", return_value={})
    @patch("post_checklists.load_checklists", return_value=SAMPLE_CHECKLISTS)
    @patch("post_checklists.get_repo_and_pr")
    @patch("post_checklists.get_github_client")
    def test_creates_new_comment(
        self, mock_gh, mock_repo_pr, mock_load, mock_existing, mock_status
    ):
        repo = MagicMock()
        pr = MagicMock()
        pr.head.sha = "abc123"
        pr.get_files.return_value = [_make_file("src/api/handler.py")]
        mock_repo_pr.return_value = (repo, pr)

        main()

        pr.create_issue_comment.assert_called_once()
        body = pr.create_issue_comment.call_args[0][0]
        assert "api-review" in body
        mock_status.assert_called_with(
            repo,
            "abc123",
            "pending",
            "1 checklist(s) require reviewer acknowledgement",
        )

    @patch("post_checklists.set_commit_status")
    @patch("post_checklists.load_checklists", return_value=SAMPLE_CHECKLISTS)
    @patch("post_checklists.get_repo_and_pr")
    @patch("post_checklists.get_github_client")
    def test_updates_existing_comment_when_body_changed(
        self, mock_gh, mock_repo_pr, mock_load, mock_status
    ):
        repo = MagicMock()
        pr = MagicMock()
        pr.head.sha = "abc123"
        pr.get_files.return_value = [_make_file("src/api/handler.py")]

        existing_comment = MagicMock()
        existing_comment.body = "old body"
        pr.get_issue_comments.return_value = [
            MagicMock(
                body="<!-- review-checklist:api-review --> old",
                id=100,
            )
        ]

        with patch(
            "post_checklists.find_existing_checklist_comments",
            return_value={"api-review": existing_comment},
        ):
            mock_repo_pr.return_value = (repo, pr)
            main()

        existing_comment.edit.assert_called_once()

    @patch("post_checklists.set_commit_status")
    @patch("post_checklists.load_checklists", return_value=SAMPLE_CHECKLISTS)
    @patch("post_checklists.get_repo_and_pr")
    @patch("post_checklists.get_github_client")
    def test_skips_update_when_body_unchanged(
        self, mock_gh, mock_repo_pr, mock_load, mock_status
    ):
        repo = MagicMock()
        pr = MagicMock()
        pr.head.sha = "abc123"
        pr.get_files.return_value = [_make_file("src/api/handler.py")]

        # Import to build expected body
        from helpers import make_checklist_comment_body

        expected_body = make_checklist_comment_body(SAMPLE_CHECKLISTS[0])

        existing_comment = MagicMock()
        existing_comment.body = expected_body

        with patch(
            "post_checklists.find_existing_checklist_comments",
            return_value={"api-review": existing_comment},
        ):
            mock_repo_pr.return_value = (repo, pr)
            main()

        existing_comment.edit.assert_not_called()

