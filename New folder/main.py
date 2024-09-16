import discord
import requests
import asyncio
import matplotlib.pyplot as plt
from discord.ext import tasks

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Create a Discord client
client = discord.Client(intents=intents)

# In-memory storage for price alerts
alerts = {}

# Helper function to get the real-time crypto price
def get_crypto_price(crypto):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies=inr"
    response = requests.get(url)
    data = response.json()

    if crypto in data:
        return data[crypto]["inr"]
    return None

# Helper function to get 7-day price change percentage
def get_crypto_change(crypto):
    url = f"https://api.coingecko.com/api/v3/coins/{crypto}/market_chart?vs_currency=inr&days=7"
    response = requests.get(url)
    data = response.json()

    if 'prices' in data:
        start_price = data['prices'][0][1]
        end_price = data['prices'][-1][1]
        price_change = (end_price - start_price) / start_price * 100
        return round(price_change, 2)
    return None

# Helper function to get detailed cryptocurrency information
def get_crypto_info(crypto):
    url = f"https://api.coingecko.com/api/v3/coins/{crypto}"
    response = requests.get(url)
    data = response.json()

    if 'market_data' in data:
        price = data['market_data']['current_price']['inr']
        market_cap = data['market_data']['market_cap']['inr']
        volume = data['market_data']['total_volume']['inr']
        rank = data['market_cap_rank']
        return f"Price: ${price}\nMarket Cap: ${market_cap}\nVolume: ${volume}\nRank: {rank}"
    return None

# Helper function to plot price trend and save it as an image
def plot_price_trend(crypto):
    url = f"https://api.coingecko.com/api/v3/coins/{crypto}/market_chart?vs_currency=inr&days=7"
    response = requests.get(url)
    data = response.json()

    if 'prices' in data:
        times = [point[0] for point in data['prices']]
        prices = [point[1] for point in data['prices']]

        plt.plot(times, prices)
        plt.xlabel('Time (ms since epoch)')
        plt.ylabel(f'{crypto.capitalize()} Price (INR)')
        plt.title(f'{crypto.capitalize()} Price Trend (Last 7 Days)')
        plt.savefig(f'{crypto}_trend.png')
        plt.close()
        return f'{crypto}_trend.png'
    return None

# Background task to check prices and send alerts
async def check_prices():
    await client.wait_until_ready()
    while not client.is_closed():
        for crypto, (channel, target) in alerts.items():
            price = get_crypto_price(crypto)
            if price and price >= target:
                await channel.send(f"🚨 {crypto.capitalize()} has reached ₹{target}! Current price: ₹{price} INR")
                del alerts[crypto]
        await asyncio.sleep(60)  # Check every 60 seconds

# Background task to send daily summary
@tasks.loop(hours=24)
async def send_daily_summary():
    channel = discord.utils.get(client.get_all_channels(), name="general")
    if channel:
        cryptos = ["bitcoin", "ethereum", "dogecoin"]
        summary = "📊 **Daily Crypto Summary:**\n"
        for crypto in cryptos:
            price = get_crypto_price(crypto)
            if price:
                summary += f"**{crypto.capitalize()}**: ₹{price} INR\n"
        await channel.send(summary)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    send_daily_summary.start()  # Start the daily summary task
    client.loop.create_task(check_prices())  # Start the price alert checking task

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # !crypto <name1> <name2> ...
    if message.content.startswith("!crypto"):
        cryptos = message.content.split()[1:]  # Get list of cryptocurrencies
        if not cryptos:
            await message.channel.send("Please specify one or more cryptocurrencies, e.g., `!crypto bitcoin ethereum`")
            return
        
        for crypto in cryptos:
            price = get_crypto_price(crypto)
            if price:
                await message.channel.send(f"The current price of {crypto} is ₹{price} INR")
            else:
                await message.channel.send(f"Could not find price for {crypto}. Please try again.")

    # !setalert <crypto> <price>
    elif message.content.startswith("!setalert"):
        try:
            _, crypto, target_price = message.content.split()
            target_price = float(target_price)
            alerts[crypto] = (message.channel, target_price)
            await message.channel.send(f"Alert set for {crypto} at ₹{target_price} INR")
        except ValueError:
            await message.channel.send("Invalid command. Use `!setalert <crypto> <target_price>`.")

    # !info <crypto>
    elif message.content.startswith("!info"):
        try:
            crypto = message.content.split()[1]
            crypto_info = get_crypto_info(crypto)
            if crypto_info:
                await message.channel.send(crypto_info)
            else:
                await message.channel.send("Cryptocurrency not found.")
        except IndexError:
            await message.channel.send("Please specify a cryptocurrency, e.g., `!info bitcoin`")

    # !trend <crypto>
    elif message.content.startswith("!trend"):
        try:
            crypto = message.content.split()[1]
            plot = plot_price_trend(crypto)
            if plot:
                await message.channel.send(file=discord.File(plot))
            else:
                await message.channel.send(f"Could not generate trend for {crypto}.")
        except IndexError:
            await message.channel.send("Please specify a cryptocurrency, e.g., `!trend bitcoin`")

    # !help
    elif message.content.startswith("!help"):
        help_text = """
        **Crypto Bot Commands:**
        `!crypto <name>` - Get the current price of a cryptocurrency
        `!setalert <name> <price>` - Set a price alert
        `!trend <name>` - Get a graph of the price trend over the last 7 days
        `!info <name>` - Get detailed information about a cryptocurrency
        `!help` - Get this help message
        """
        await message.channel.send(help_text)

# Run the bot
client.run('MTI4NDUzMTA1MjQ1MDE1MjQ4MA.GL-_fv.rG3vAlSSWw5u79hFNyxEQtT68md4miEQTLafwo')