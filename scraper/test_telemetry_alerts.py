"""Alarm bildirimi yalnızca alarm YENİ açıldığında gitmeli.

Açık bir alarm her koşuda yeniden `create_system_alert`'ten geçer. Her geçişte
bildirim atılsaydı kabul edilmiş Shell arızası Discord kanalını doldurur ve
kanal, gerçek bir arızanın görülemeyeceği bir gürültüye dönüşürdü.
"""

import contextlib
import io
import unittest
import unittest.mock

import telemetry


class _FakeQuery:
    def __init__(self, table):
        self.table = table
        self.action = "select"

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def insert(self, payload):
        self.action = "insert"
        self.table.inserted.append(payload)
        return self

    def update(self, payload):
        self.action = "update"
        self.table.updated.append(payload)
        return self

    def execute(self):
        if self.table.error:
            raise self.table.error
        data = self.table.existing if self.action == "select" else []
        return unittest.mock.Mock(data=data)


class _FakeClient:
    def __init__(self, existing=None, error=None):
        self.existing = existing or []
        self.error = error
        self.inserted = []
        self.updated = []

    def table(self, _name):
        return _FakeQuery(self)


class AlertNotificationTest(unittest.TestCase):
    def _create(self, client):
        with unittest.mock.patch.object(telemetry, "supabase", client), \
             unittest.mock.patch.object(telemetry, "_send_discord_webhook") as send, \
             contextlib.redirect_stdout(io.StringIO()):
            telemetry.create_system_alert(
                severity="critical", source="bot:x.py", title="x failed", message="m"
            )
        return send

    def test_new_alert_notifies_once(self):
        client = _FakeClient()
        send = self._create(client)
        self.assertEqual(len(client.inserted), 1)
        send.assert_called_once_with("x failed", "m", "critical")

    def test_already_open_alert_is_refreshed_silently(self):
        client = _FakeClient(existing=[{"id": 7}])
        send = self._create(client)
        self.assertEqual(len(client.updated), 1)
        send.assert_not_called()

    def test_database_failure_still_notifies(self):
        send = self._create(_FakeClient(error=RuntimeError("baglanti koptu")))
        send.assert_called_once()

    def test_no_client_still_notifies(self):
        send = self._create(None)
        send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
