from .base import Module, Command
from discord import Embed
import json
import time


class Steam(Module):
    def __init__(self, host, *args, **kwargs):
        super().__init__(host, *args, **kwargs)
        self.api_key = load_api_key()

    @Command.register(name="steamid")
    async def steamid(host, state):
        await state.message.channel.trigger_typing()
        args = Command.split(state.content)
        userID = args[1]
        response = await state.command_host.steam_profile_request(userID)
        # make status check
        #   There's not really a way for the function to halt up. We could throw an exception on 404 but that's a bit lame
        if response is None:
            # we're going to assume the user put a vanity URL and send the request again.
            resp = await Module._http_get_request(f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?key={state.command_host.api_key}&vanityurl={userID}")
            url = json.loads(resp['text'])['response']
            if url['success'] != 1:
                await state.message.channel.send("User not found.")
                return
            userID = url['steamid']
            response = await state.command_host.steam_profile_request(userID)
        url = f"https://api.steampowered.com/IPlayerService/GetBadges/v1/?key={state.command_host.api_key}&steamid={userID}"
        timecreated = time.strftime("%B %d, %Y", time.gmtime(response['timecreated']))
        resp = await Module._http_get_request(url)
        response_badge = json.loads(resp['text'])['response']
        desc = f"**On steam since:** {timecreated}\n**Badge Count:** {len(response_badge['badges'])}\n**User XP:** {response_badge['player_xp']}\n**Level:** {response_badge['player_level']}\n"
        response_embed = Embed(title=response['personaname'],
                               type="rich",
                               description=desc,
                               url=response['profileurl'],
                               color=0x00adee)
        response_embed.set_thumbnail(url=response['avatarfull'])
        await state.message.channel.send(embed=response_embed)

    async def steam_profile_request(self, steamID):
        url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v1/?key={self.api_key}&steamids={steamID}"
        response = await Module._http_get_request(url)
        result = json.loads(response['text'])['response']['players']['player'][0]
        return result


def load_api_key():
    api_key = ""
    with open("./steam_api.txt") as steam:
        api_key = steam.read().strip()
    # get SteamID from customURL
    return api_key
