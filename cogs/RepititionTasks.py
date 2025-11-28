from disnake.ext import commands, tasks
import disnake
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import datetime
from config import GuldID, BeforeShiftAlarmTime, EndingShiftAlarmTime, FinishedShiftAlarmTime, ColdCallerRoleID, ClockingChannelID
import datetime
from zoneinfo import ZoneInfo

load_dotenv()

class ClockInView(disnake.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.add_item(ClockInButton(bot))

class ClockOutView(disnake.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.add_item(ClockOutButton(bot))

class ClockInButton(disnake.ui.Button):
    def __init__(self, bot: commands.Bot):
        self.client = MongoClient(os.getenv("DATABASE_URL"))
        self.db = self.client["Grove"]
        self.ClockedUsers = self.db.get_collection("ClockedUsers")
        self.ClockedStats = self.db.get_collection("ClockedStats")
        self.bot = bot
        super().__init__(label="Clock In Now", style=disnake.ButtonStyle.green, emoji="⏰")

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer(with_message=True)

        # Check if the user has clocked in, if they have then tell them to clockout first, else allow them to clock in.

        exists = self.ClockedUsers.find_one({"user_id": inter.user.id})
        print("Hello")
        if exists:

            print("Hwllo")

            embed = disnake.Embed(
                title="Error!",
                description="You're already clocked in, please clock yourself out before running the command again!",
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

class ClockOutButton(disnake.ui.Button):
    def __init__(self, bot: commands.Bot):
        self.client = MongoClient(os.getenv("DATABASE_URL"))
        self.db = self.client["Grove"]
        self.ClockedUsers = self.db.get_collection("ClockedUsers")
        self.ClockedStats = self.db.get_collection("ClockedStats")
        self.bot = bot
        super().__init__(label="Clock Out Now", style=disnake.ButtonStyle.red, emoji="⏰")

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer(with_message=True)

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

class RepititionTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.client = MongoClient(os.getenv("DATABASE_URL"))
        self.db = self.client["Grove"]
        self.ClockedUsers = self.db.get_collection("ClockedUsers")
        self.ClockedStats = self.db.get_collection("ClockedStats")
        self.bot = bot
        self.status_task.start()

    def cog_unload(self):
        self.status_task.cancel()

    @tasks.loop(seconds=60)
    async def status_task(self):

        # Check if the time is 11:50 AM EST, if it is then tell all the employees to clock in, if it is 4:45 PM EST then tell the users to clock out, if they haven't clocked out by 5 PM EST then clock them out automatically

        cards = list(self.ClockedStats.find({}))
        
        print(cards)

        if len(cards) == 0:
            return

        for card in cards:
            guild = await self.bot.fetch_guild(GuldID)

            member = await guild.fetch_member(int(card["user_id"]))

            est_time = datetime.datetime.now(ZoneInfo("America/New_York"))
            formatted_time = est_time.strftime("%H:%M")

            print(formatted_time)

            ColdCallerRole = self.bot.get_guild(GuldID).get_role(ColdCallerRoleID)

            if member.get_role(ColdCallerRole.id):
                if formatted_time == BeforeShiftAlarmTime:
                    embed = disnake.Embed(
                        title="⏰ Shift Reminder!",
                        description=f"Hey {member.mention}, your shift starts in 10 minutes (12 PM EST)! Don’t forget to clock in and get ready to crush today’s calls",
                        color=disnake.Color.green(),
                        timestamp=datetime.datetime.now()
                    )

                    embed.set_footer(text="Powered by Grove bot.")

                    await member.send(embed=embed, view=ClockInView(self.bot))
                
                if formatted_time == EndingShiftAlarmTime and self.ClockedUsers.find_one({"user_id": member.id}):
                    embed = disnake.Embed(
                        title="⏰ Shift Ending Soon!",
                        description=f"Hey {member.mention}, your shift ends in 15 minutes (5 PM EST)! Please make sure to wrap up your calls and clock out on time to ensure your hours are recorded correctly.",
                        color=disnake.Color.orange(),
                        timestamp=datetime.datetime.now()
                    )

                    embed.set_footer(text="Powered by Grove bot.")

                    await member.send(embed=embed)
                
                if formatted_time == FinishedShiftAlarmTime and self.ClockedUsers.find_one({"user_id": member.id}):

                    # Check if the user has a stats card, if they dont make one automatically for them
        
                    exists = self.ClockedStats.find_one({"user_id": member.id})

                    if not exists:
                    
                        self.ClockedStats.insert_one({
                            "user_id": member.id,
                            "total_time": 0
                        })

                    # Send a message to the logs channel

                    ClockOutChannel = self.bot.get_channel(ClockingChannelID)

                    embed = disnake.Embed(
                        title="A user has clocked out!",
                        description=f"{member.mention} has clocked out!",
                        color=disnake.Color.red(),
                        timestamp=datetime.datetime.now()
                    )

                    embed.set_author(name=member.name, icon_url=member.display_avatar.url)
                    embed.set_thumbnail(url=member.display_avatar.url)

                    await ClockOutChannel.send(embed=embed)

                    # Increment the user's stats by the amount of time they've clocked in by fetching the time they've clocked in at and subtracting it from the current time

                    ClockedUsersCard = self.ClockedUsers.find_one({"user_id": member.id})

                    createdtime = ClockedUsersCard["clocked_time"]
                    currenttime = datetime.datetime.now().timestamp()

                    self.ClockedStats.update_one(
                        {"user_id": member.id},
                        {"$inc": {"total_time": currenttime - createdtime}}
                    )

                    # Allow the user to clock out

                    self.ClockedUsers.delete_one({
                        "user_id": member.id
                    })
        

    @status_task.before_loop
    async def before_status_task(self):
        print("Waiting for bot to be ready...")
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ClockInView(self.bot))
        self.bot.add_view(ClockOutView(self.bot))

def setup(bot: commands.bot):
    bot.add_cog(RepititionTask(bot))
