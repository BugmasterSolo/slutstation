from lxml import html
import aiohttp
import asyncio
import aiomysql
import json
import re
import random
import math


async def scrape():
    ANGLER_URL = "http://ff14angler.com"
    fishes = []
    locationsum = [0] * 8
    async with aiohttp.ClientSession() as session:
        for i in range(34):
            print(f"scraping page {i + 1}...")
            async with session.get(f"{ANGLER_URL}/book/{i + 1}") as resp:
                text = await resp.text()
                text = re.sub("<br>", "\n", text)
                text = re.sub("\\n\\n\[.*\]|\\n\\n※.*|<\/?i>", "", text)
                tree = html.fromstring(text)
                fishname = tree.xpath("//td[@id='book_guide']/table//span[@class='name']/text()")
                fishdesc = tree.xpath("//td[@id='book_guide']/table/tr[3]/td/text()")
                fishildata = tree.xpath("//td[@id='book_guide']/table/tr[2]//span[@class='ilevel']/text()")
                fishlode = tree.xpath("//a[@class='lodestone eorzeadb_link']/@href")
                fishcbh = tree.xpath("//table[@class='grid']//a/@href")
                fishil = []
                print(len(fishcbh))
                for item in fishildata:
                    il = None
                    try:
                        il = re.findall('\d+', item)[0]
                    except IndexError:
                        pass
                    if il:
                        fishil.append(il)
                for j in range(len(fishname)):
                    print(f"Parsing fish {len(fishes) + 1}...")
                    fishlen = None
                    fishtug = None
                    print("Scraping angler page...")
                    async with session.get(f"{ANGLER_URL}{fishcbh[j]}") as respang:
                        angtext = await respang.text()
                        treeang = html.fromstring(angtext)
                        fishlen = treeang.xpath("//span[@class='ilm']/text()")
                        fishtug = treeang.xpath("//canvas[@class='tug_graph']/@data-value")
                        if len(fishlen) == 0:
                            fishlen = 9999.9
                        else:
                            fishlen = fishlen[0]

                        if len(fishtug) == 0:
                            fishtug = 13.0
                        else:
                            tug_json = json.loads(fishtug[0])
                            avg = 0
                            weightsum = 0
                            for key in tug_json:
                                weight = tug_json[key]
                                avg += int(key) * weight
                                weightsum += weight
                            fishtug = avg / weightsum
                    print("Scraping lodestone...")
                    async with session.get(fishlode[j]) as respfish:
                        fishtext = await respfish.text()
                        treelode = html.fromstring(fishtext)
                        fishprice = treelode.xpath("//span[@class='sys_nq_element']/text()")
                        if len(fishprice) == 0 or "gil" not in fishprice[0]:
                            fishprice = "0"
                        else:
                            fishprice = re.sub("\,", "", fishprice[0])
                    locid = random.randint(0, 7)
                    weight = 100 * math.exp(5 - float(fishtug))
                    locationsum[locid] += weight
                    fishes.append({
                        'name': fishname[j],
                        'descrip': fishdesc[j],
                        'il': int(fishil[j]),
                        'length': float(fishlen),
                        'unweight': weight,
                        'location': locid,
                        'price': int(re.match("(\d|\,)+", fishprice).group(0))
                    })
                    # print(fishes[len(fishes) - 1])
    return fishes, locationsum


async def process_db(json_list, db, locationsum):
    LOCATIONS = ("LAKE", "RIVER", "OCEAN", "BEACH", "POND", "OASIS", "SPRING", "???")
    # SIZE_KEYWORDS = {
    #     'tiny': "TINY",
    #     'small': "SMALL",
    #     'large': "LARGE",
    #     'big': "LARGE",
    #     'massive': "MASSIVE"
    # }
    # KEYWORD_TINY = ("schools", "miniscule", "worm")
    # KEYWORD_SMALL = ("mollusk", "crab", "urchin", "cephalopod", "snail", "fish", "catfish", "goldfish")
    # KEYWORD_MEDIUM = ("bottom", "freshwater fish", "eel", "salmon")
    # KEYWORD_LARGE = ("sizable", "king", "lord", "queen", "bass", "shark", "large")
    async with db.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("TRUNCATE TABLE fishdb")
            for item in json_list:
                rarity = 1
                weight = item['unweight'] * 100 / locationsum[item['location']]
                if weight < 2:
                    rarity = 2
                    if weight < 0.4:
                        rarity = 3
                        if weight < 0.05:
                            rarity = 4
                            if weight < 0.01:
                                rarity = 5
                print("rarity: " + str(rarity))
                query = "INSERT INTO fishdb (name, description, location, size_min_two, size_max_two, rarity, catch_weight) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                await cur.execute(query, (item['name'], item['descrip'], LOCATIONS[item['location']], item['length'] * 0.7, item['length'] * 0.9, rarity, weight))
        await conn.commit()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    fishy, locsum = loop.run_until_complete(scrape())
    with open("../../db_token.json", "r") as f:
        sql_cred_array = json.loads(f.read().strip())
    db = loop.run_until_complete(aiomysql.create_pool(loop=loop, **sql_cred_array))  # minsize = 0?
    loop.run_until_complete(process_db(fishy, db, locsum))

    #
    # with open('fishlist.json', 'w') as file:
    #     file.write(json.dumps(fishy))
    # print("donezo")
