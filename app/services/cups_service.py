from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class CUPSServiceError(Exception):
    pass


@dataclass
class CUPSJobState:
    cups_job_id: str
    state: str


class CUPSService:
    def __init__(self, cups_server: str, printer_name: str) -> None:
        self.cups_server = cups_server
        self.printer_name = printer_name

    def submit_job(self, file_path: Path, title: str, copies: int) -> str:
        command = [
            "lp",
            "-h",
            self.cups_server,
            "-d",
            self.printer_name,
            "-n",
            str(copies),
            "-t",
            title,
            str(file_path),
        ]
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, env=self._command_env()
        )
        if result.returncode != 0:
            raise CUPSServiceError("Failed to queue print job.")
        match = re.search(r"request id is [^-]+-(\d+)", result.stdout)
        if not match:
            raise CUPSServiceError("Failed to parse CUPS job id.")
        return match.group(1)

    def fetch_job_states(self) -> list[CUPSJobState] | None:
        command = ["lpstat", "-h", self.cups_server, "-W", "not-completed", "-o", self.printer_name]
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, env=self._command_env()
        )
        if result.returncode != 0:
            return None

        states: list[CUPSJobState] = []
        for line in result.stdout.splitlines():
            match = re.match(rf"{re.escape(self.printer_name)}-(\d+)\s+", line)
            if match:
                states.append(CUPSJobState(cups_job_id=match.group(1), state="active"))
        return states

    def check_printer_reachability(self) -> tuple[bool, str | None]:
        command = ["lpstat", "-h", self.cups_server, "-p", self.printer_name]
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, env=self._command_env()
        )
        if result.returncode != 0:
            return False, "CUPS command failed."
        output = result.stdout.strip().lower()
        if "disabled" in output or "not accepting requests" in output:
            return False, "Printer is not accepting jobs."
        return True, None

    def _command_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["CUPS_SERVER"] = self.cups_server
        return env
