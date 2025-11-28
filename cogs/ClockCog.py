from pymongo import MongoClient
import os
from dotenv import load_dotenv
from disnake.ext import commands
import disnake
from config import ClockingChannelID
import datetime

load_dotenv()


class ClockCog(commands.Cog):
    
    def __init__(self, bot: commands.Bot):
        self.client = MongoClient(os.getenv("DATABASE_URL"))
        self.bot = bot
        self.db = self.client["Grove"]
        self.ClockedUsers = self.db.get_collection("ClockedUsers")
        self.ClockedStats = self.db.get_collection("ClockedStats")

        super().__init__()

    async def cog_slash_command_error(self, inter, error):
        if isinstance(error, commands.CommandOnCooldown):
            await inter.response.send_message("You're in cooldown, please try again later!", ephemeral=True)

    @commands.slash_command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def clockin(self, inter: disnake.ApplicationCommandInteraction):
        
        await inter.response.defer(ephemeral=True)

        # Check if the user has clocked in, if they have then tell them to clockout first, else allow them to clock in.

        exists = self.ClockedUsers.find_one({"user_id": inter.user.id})

        if exists:

            embed = disnake.Embed(
                title="Error!",
                description="You're already clocked in, please clock yourself out before running the command again again!",
                timestamp=datetime.datetime.now(),
                color=disnake.Color.red()
            )

            embed.set_footer(text="Powered by Grove bot.")

            await inter.edit_original_response(embed=embed)

            return

        else:

            self.ClockedUsers.insert_one({
                "user_id": inter.user.id,
                "clocked_time": datetime.datetime.now().timestamp(),
                "warned": False
            })

        # Check if the user has a stats card, if they dont make one automatically for them
        
        exists = self.ClockedStats.find_one({"user_id": inter.user.id})

        if not exists:

            self.ClockedStats.insert_one({
                "user_id": inter.user.id,
                "total_time": 0
            })

        # Send a message to the logs channel

        ClockInChannel = self.bot.get_channel(ClockingChannelID)
        
        embed = disnake.Embed(
            title="A user has clocked in!",
            description=f"{inter.user.mention} has clocked in!",
            color=disnake.Color.green(),
            timestamp=datetime.datetime.now()
        )

        embed.set_author(name=inter.user.name, icon_url=inter.user.display_avatar.url)
        embed.set_thumbnail(url=inter.user.display_avatar.url)

        await ClockInChannel.send(embed=embed)

        # Inform the user that they successfully clocked in!

        embed = disnake.Embed(
            title="You have clocked in!",
            description=f"You have successfully clocked in!",
            color=disnake.Color.green(),
            timestamp=datetime.datetime.now()
        )

        await inter.edit_original_response(embed=embed)

    @commands.slash_command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def clockout(self, inter: disnake.ApplicationCommandInteraction):
        
        await inter.response.defer(ephemeral=True)

        # Check if the user has a stats card, if they dont make one automatically for them
        
        exists = self.ClockedStats.find_one({"user_id": inter.user.id})

        if not exists:

            self.ClockedStats.insert_one({
                "user_id": inter.user.id,
                "total_time": 0
            })

        # Check if the user is clocked out or not, if they are then ask them to clock in
        
        exists = self.ClockedUsers.find_one({"user_id": inter.user.id})

        if not exists:

            embed = disnake.Embed(
                title="Error!",
                description="You're already clocked out or you haven't clocked in, please clock yourself in before running the command again again!",
                timestamp=datetime.datetime.now(),
                color=disnake.Color.red()
            )

            embed.set_footer(text="Powered by Grove bot.")

            await inter.edit_original_response(embed=embed)

            return

        # Send a message to the logs channel

        ClockOutChannel = self.bot.get_channel(ClockingChannelID)
        
        embed = disnake.Embed(
            title="A user has clocked out!",
            description=f"{inter.user.mention} has clocked out!",
            color=disnake.Color.red(),
            timestamp=datetime.datetime.now()
        )

        embed.set_author(name=inter.user.name, icon_url=inter.user.display_avatar.url)
        embed.set_thumbnail(url=inter.user.display_avatar.url)

        await ClockOutChannel.send(embed=embed)

        # Increment the user's stats by the amount of time they've clocked in by fetching the time they've clocked in at and subtracting it from the current time

        ClockedUsersCard = self.ClockedUsers.find_one({"user_id": inter.user.id})

        createdtime = ClockedUsersCard["clocked_time"]
        currenttime = datetime.datetime.now().timestamp()

        self.ClockedStats.update_one(
            {"user_id": inter.user.id},
            {"$inc": {"total_time": currenttime - createdtime}}
        )

        # Allow the user to clock out

        self.ClockedUsers.delete_one({
            "user_id": inter.user.id
        })

        # Inform the user that they successfully clocked out!

        embed = disnake.Embed(
            title="You have clocked out!",
            description=f"You have successfully clocked out!",
            color=disnake.Color.red(),
            timestamp=datetime.datetime.now()
        )

        await inter.edit_original_response(embed=embed)

    @commands.slash_command()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def hours(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)

        exists = self.ClockedStats.find_one({"user_id": inter.user.id})

        if not exists:
            self.ClockedStats.insert_one({
                "user_id": inter.user.id,
                "total_time": 0
            })

        UserClockedStats = self.ClockedStats.find_one({"user_id": inter.user.id})

        embed = disnake.Embed(title="Total Clocked Hours", color=disnake.Color.green())

        embed.add_field(name="Total Hours Clocked", value=f"{str(datetime.timedelta(seconds=int(UserClockedStats["total_time"])))}", inline=False)

        embed.set_thumbnail(url=inter.user.display_avatar.url)
        embed.set_footer(text="Powered by Grove bot.")

        await inter.edit_original_response(embed=embed)
    
def setup(bot: commands.Bot):
    bot.add_cog(ClockCog(bot))