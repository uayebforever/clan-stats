import os
from datetime import datetime
from typing import Sequence, Optional

import aiohttp
from pydantic import BaseModel, TypeAdapter

TRIALS_REPORT_URL = (os.environ["DESTINY_TRIALS_REPORT_URL"]
                     if "DESTINY_TRIALS_REPORT_URL" in os.environ
                     else "https://elastic.destinytrialsreport.com/")


class DestinyTrialsReportException(RuntimeError):
    pass


class TrialsReportPlayer(BaseModel):
    """	{
		"bnetId": 0,
		"bungieName": "foreverpizzamike#1126",
		"displayName": "foreverpizzamike",
		"membershipId": "4611686018522648296",
		"membershipType": 2,
		"crossSaveOverride": {
			"membershipId": "",
			"membershipType": 0
		},
		"emblemHash": 1907674139,
		"lastPlayed": "2022-05-05T04:59:03Z",
		"score": 1
	},"""

    bnetId: int
    bungieName: Optional[str]
    displayName: str
    membershipId: str
    membershipType: int
    lastPlayed: datetime

async def search_players(search_string: str) -> Sequence[TrialsReportPlayer]:
    async with aiohttp.ClientSession() as session:
        async with session.get(player_search_url(search_string)) as response:
            if response.status not in (200,):
                raise DestinyTrialsReportException(response)
            data = await response.text()
    result = TypeAdapter(list[TrialsReportPlayer])
    return result.validate_json(data)


def player_search_url(search_string: str, membership_type: int = 0) -> str:
    return "{root}players/{mtype}/{search}".format(
        root=TRIALS_REPORT_URL,
        mtype=membership_type,
        search=search_string
    )
