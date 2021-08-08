import discord, json, asyncio, random, math, sqlite3
from discord.ext import commands

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        try:
            with open('db/reaction_roles.json', 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.bot.loop.create_task(self.create())
        try:
            with open('db/emojis.json', 'r') as f:
                self.emojis = json.load(f)['games']
        except FileNotFoundError:
            self.enmojis = {}

        self.conn = sqlite3.connect('db/details.db')
        self.c = self.conn.cursor()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        flag = False
        for reaction_role in self.data[str(payload.guild_id)]:
            if payload.emoji.is_unicode_emoji():
                emoji = str(payload.emoji)
            else:
                emoji = payload.emoji.id
            if [payload.message_id, emoji] == [reaction_role['message_id'], reaction_role['emoji']]:
                flag = True
                break
        if not flag:
            return

        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(reaction_role['role_id'])
        if role:
            await payload.member.add_roles(role)
        else:
            self.data[str(payload.guild_id)].remove(reaction_role)
            self.save()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        flag = False
        for reaction_role in self.data[str(payload.guild_id)]:
            if payload.emoji.is_unicode_emoji():
                emoji = str(payload.emoji)
            else:
                emoji = payload.emoji.id
            if [payload.message_id, emoji] == [reaction_role['message_id'], reaction_role['emoji']]:
                flag = True
                break
        if not flag:
            return
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = guild.get_role(reaction_role['role_id'])
        if role:
            await member.remove_roles(role)
        else:
            self.data[str(payload.guild_id)].remove(reaction_role)
            self.save()

    async def cog_check(self, ctx):
        return await self.bot.moderatorCheck(ctx)

    @commands.group(brief='This adds/removes roles from a user based on reactions to a specified message', aliases=['rr'])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def reactionrole(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.reply('Invalid command passed.')
            return

    @reactionrole.command(brief='Adds a reaction role')
    async def add(self, ctx, message: discord.Message, role: discord.Role, *, game: str=None):
        if game:
            if game in self.emojis:
                reaction = self.emojis[game]
            else:
                await ctx.reply(f'{game} is invalid!')
                return
        else:
            msg = await ctx.reply('React to this message with the reaction you want to use for the reaction role.')
            def check(reaction, user):
                return user == ctx.author and reaction.message.id == msg.id
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                reaction = reaction.emoji
            except asyncio.TimeoutError:
                await ctx.send('Reaction role setup has been cancelled. You took too long to choose a valid reaction.')
                return
        await message.add_reaction(reaction)
        ID = self.generateID([reaction_role['ID'] for reaction_role in self.data[str(ctx.guild.id)]])
        if isinstance(reaction, str):
            if reaction[0] == '<':
                reaction = int(reaction.split(':')[2][:-1])
        else:
            reaction = reaction.id
        dict = {
            "ID": ID,
            "emoji": reaction,
            "role_id": role.id,
            "type": 1,
            "message_id": message.id,
            "channel_id": message.channel.id
        }
        self.data[str(ctx.guild.id)].append(dict)
        self.save()
        embed = discord.Embed(
            description = 'Successfully created the reaction role!',
            color = discord.Color.blurple()
        )
        embed.add_field(name='ID', value=f'`{ID}`')
        if game:
            await ctx.reply(embed=embed)
        else:
            await msg.edit(content=None, embed=embed)

    @reactionrole.command(brief='Removes a reaction role')
    async def remove(self, ctx, ID: str):
        for reaction_role in self.data[str(ctx.guild.id)]:
            if ID == reaction_role['ID']:
                channel = self.bot.get_channel(reaction_role['channel_id'])
                message = await channel.fetch_message(reaction_role['message_id'])
                if isinstance(emoji := reaction_role['emoji'], int):
                    for game in self.emojis:
                        if str(emoji) in self.emojis[game]:
                            emoji = self.emojis[game]
                            break
                await message.remove_reaction(emoji, self.bot.user)
                self.data[str(ctx.guild.id)].remove(reaction_role)
                self.save()
                await ctx.send(f'Reaction role with ID `{ID}` removed successfully!')
                return
        await ctx.reply(f'No reaction role with ID `{ID}` found.')

    def generateID(self, IDs):
        sample_set = '01234567890123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        ID = ''
        for _ in range(5):
            ID += sample_set[math.floor(random.random() * 72)]
        if ID in IDs:
            return self.generateID(IDs)
        else:
            return ID

    async def create(self):
        await self.bot.wait_until_ready()
        self.data = dict([(guild.id, []) for guild in self.bot.guilds])
        self.save()

    def save(self):
        with open('db/reaction_roles.json', 'w') as f:
            json.dump(self.data, f)

def setup(bot):
    bot.add_cog(ReactionRoles(bot))
