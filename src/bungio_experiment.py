import asyncio
import os
from typing import Sequence

from bungio import Client
from bungio.models import BungieMembershipType, DestinyActivityModeType, DestinyUser, DestinyClan, \
    DestinyProfileResponse

from clan_stats.config import read_config, ClanStatsConfig
from clan_stats.data.retrieval.bungio_data_retriever import BungioDataRetriever

config = read_config()

# create the client obj with our bungie authentication
client = Client(
    bungie_client_id="",
    bungie_client_secret="",
    bungie_token=config.bungie_api_key,
)


async def main():
    # # create a user obj using a known bungie id
    # user = DestinyUser(membership_id=4611686018467765462, membership_type=BungieMembershipType.TIGER_STEAM)
    #
    # # iterate thought the raids that user has played
    # async for activity in user.yield_activity_history(mode=DestinyActivityModeType.RAID):
    #
    #     # print the date of the activity
    #     print(activity.period)
    clan = DestinyClan(group_id=config.default_clan_id)

    members = await clan.get_members_of_group(currentpage=1, member_type=0, name_search="")

    characters: Sequence[DestinyProfileResponse] = await asyncio.gather(*[
        client.api.get_profile(destiny_membership_id=m.destiny_user_info.membership_id,
                               membership_type=m.destiny_user_info.membership_type,
                               components=[200]) for m in members.results])
    for c in characters:
        print(c.characters.data.keys())


async def main2():
    retriever = BungioDataRetriever(config.bungie_api_key)
    clan = await retriever.get_clan(config.default_clan_id)
    for c in clan.characters:
        print(c.character_id)


# bungio is by nature asynchronous, it can only be run in an asynchronous context

if __name__ == "__main__":
    asyncio.run(main2())
