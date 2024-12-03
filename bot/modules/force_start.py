from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import (
    OWNER_ID,
    bot,
    queued_dl,
    queued_up,
    task_dict,
    user_data,
    task_dict_lock,
    queue_dict_lock,
)
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import get_task_by_gid
from bot.helper.ext_utils.task_manager import (
    start_dl_from_queued,
    start_up_from_queued,
)
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import send_message


@new_task
async def remove_from_queue(_, message):
    user_id = message.from_user.id if message.from_user else message.sender_chat.id
    msg = message.text.split()
    status = msg[1] if len(msg) > 1 and msg[1] in ["fd", "fu"] else ""
    if (status and len(msg) > 2) or (not status and len(msg) > 1):
        gid = msg[2] if status else msg[1]
        task = await get_task_by_gid(gid)
        if task is None:
            await send_message(message, f"GID: <code>{gid}</code> Not Found.")
            return
    elif reply_to_id := message.reply_to_message_id:
        async with task_dict_lock:
            task = task_dict.get(reply_to_id)
        if task is None:
            await send_message(message, "This is not an active task!")
            return
    elif len(msg) in {1, 2}:
        msg = (
            "Reply to an active Command message which was used to start the download"
            f" or send <code>/{BotCommands.ForceStartCommand[0]} GID</code> to force start download and upload! Add you can use /cmd <b>fd</b> to force downlaod only or /cmd <b>fu</b> to force upload only!"
        )
        await send_message(message, msg)
        return
    if user_id not in (OWNER_ID, task.listener.user_id) and (
        user_id not in user_data or not user_data[user_id].get("is_sudo")
    ):
        await send_message(message, "This task is not for you!")
        return
    listener = task.listener
    msg = ""
    async with queue_dict_lock:
        if status == "fu":
            listener.force_upload = True
            if listener.mid in queued_up:
                await start_up_from_queued(listener.mid)
                msg = "Task have been force started to upload!"
        elif status == "fd":
            listener.force_download = True
            if listener.mid in queued_dl:
                await start_dl_from_queued(listener.mid)
                msg = "Task have been force started to download only!"
        else:
            listener.force_download = True
            listener.force_upload = True
            if listener.mid in queued_up:
                await start_up_from_queued(listener.mid)
                msg = "Task have been force started to upload!"
            elif listener.mid in queued_dl:
                await start_dl_from_queued(listener.mid)
                msg = "Task have been force started to download and upload will start once download finish!"
    if msg:
        await send_message(message, msg)


bot.add_handler(
    MessageHandler(
        remove_from_queue,
        filters=command(BotCommands.ForceStartCommand, )
        & CustomFilters.authorized,
    )
)