# async_tiktok_data_manager.py

import time
from models import AsyncSessionLocal
from models.proxy_url import ProxyUrl
from models.tiktok_relationship import TikTokRelationship
from models.tiktok_account import TikTokAccount
from models.tiktok_video_details import TikTokVideoDetails
from models.tiktok_user_details import TikTokUserDetails
from sqlalchemy.future import select
from sqlalchemy.sql import func
from typing import List

from custom_globals import Globals

class AsyncTikTokDataManager(object):
    def __init__(self):
        self.user = 'AsyncTikTokDataManager'

    async def get_active_tiktok_accounts(self) -> List[dict]:
        async with AsyncSessionLocal() as session:
            try:
                subquery = select(TikTokRelationship.tiktok_account).where(TikTokRelationship.status == True).subquery()
                query = select(
                    subquery.c.tiktok_account,
                    TikTokAccount.updated_at,
                    TikTokAccount.comments
                ).outerjoin(
                    TikTokAccount,
                    TikTokAccount.tiktok_account == subquery.c.tiktok_account
                )

                result = await session.execute(query)
                accounts = result.fetchall()

                now = time.time()
                accounts_list = []
                for account in accounts:
                    tiktok_account = account.tiktok_account
                    updated_at = account.updated_at
                    comments = account.comments

                    if updated_at is None:
                        priority_time = 0  # 不存在于 tiktok_account 表中
                    else:
                        timestamp = updated_at.timestamp()
                        if comments == '获取失败':
                            priority_time = timestamp + 1200
                        elif comments == '账号不存在':
                            priority_time = timestamp + 4200
                        else:
                            priority_time = timestamp + 600

                    if priority_time > now:
                        continue

                    accounts_list.append({
                        'account_name': tiktok_account,
                        'unique_id': tiktok_account.rsplit('@', 1)[-1].replace(' ', '') if '@' in tiktok_account else tiktok_account.replace(' ', ''),
                        'updated_at': updated_at,
                        'comments': comments,
                        'priority_time': priority_time
                    })
                accounts_list.sort(key=lambda x: x['priority_time'])
                return accounts_list
            except Exception as e:
                Globals.logger.error(f"Error occurred while fetching accounts: {e}", self.user)
                return []

    async def insert_or_update_tiktok_account(self, tiktok_account, account_data: dict):
        async with AsyncSessionLocal() as session:
            try:
                user_info = account_data.get('userInfo')
                user = user_info.get('user')
                tiktok_id = user.get('id')
                stats = user_info.get('stats')

                data = {
                    'tiktok_account': tiktok_account,
                    'tiktok_id': tiktok_id,
                    'unique_id': user.get('uniqueId'),
                    'nickname': user.get('nickname'),
                    'avatar_larger': user.get('avatarLarger'),
                    'avatar_medium': user.get('avatarMedium'),
                    'avatar_thumb': user.get('avatarThumb'),
                    'signature': user.get('signature'),
                    'verified': user.get('verified'),
                    'sec_uid': user.get('secUid'),
                    'private_account': user.get('privateAccount'),
                    'following_visibility': user.get('followingVisibility'),
                    'comment_setting': user.get('commentSetting'),
                    'duet_setting': user.get('duetSetting'),
                    'stitch_setting': user.get('stitchSetting'),
                    'download_setting': user.get('downloadSetting'),
                    'profile_embed_permission': user.get('profileEmbedPermission'),
                    'profile_tab_show_playlist_tab': user.get('profileTab', {}).get('showPlaylistTab'),
                    'commerce_user': user.get('commerceUserInfo', {}).get('commerceUser'),
                    'tt_seller': user.get('commerceUserInfo', {}).get('ttSeller'),
                    'relation': user.get('relation'),
                    'is_ad_virtual': user.get('isAdVirtual'),
                    'is_embed_banned': user.get('isEmbedBanned'),
                    'open_favorite': user.get('openFavorite'),
                    'nick_name_modify_time': user.get('nicknameModifyTime'),
                    'can_exp_playlist': user.get('canExpPlaylist'),
                    'secret': user.get('secret'),
                    'ftc': user.get('ftc'),
                    'link': user.get('bioLink', {}).get('link'),
                    'risk': user.get('bioLink', {}).get('risk'),
                    'digg_count': stats.get('diggCount'),
                    'follower_count': stats.get('followerCount'),
                    'following_count': stats.get('followingCount'),
                    'friend_count': stats.get('friendCount'),
                    'heart_count': stats.get('heartCount'),
                    'video_count': stats.get('videoCount'),
                    'updated_at': func.now(),
                    'comments': '获取成功'
                }

                existing_account = await session.get(TikTokAccount, tiktok_account)

                if existing_account:
                    for key, value in data.items():
                        setattr(existing_account, key, value)
                    await session.commit()
                else:
                    new_account = TikTokAccount(**data)
                    session.add(new_account)
                    await session.commit()

                existing_user_details = await session.get(TikTokUserDetails, tiktok_id)

                if existing_user_details:
                    for key, value in data.items():
                        setattr(existing_user_details, key, value)
                    await session.commit()
                else:
                    new_user_details = TikTokUserDetails(**data)
                    session.add(new_user_details)
                    await session.commit()

            except Exception as e:
                await session.rollback()
                Globals.logger.error(f"Error occurred while inserting/updating TikTok account: {e}", self.user)

    async def insert_or_update_tiktok_video_details(self, video_datas: list):
        async with AsyncSessionLocal() as session:
            try:
                for video_data in video_datas:
                    tiktok_video_id = video_data.get('id')
                    video_status = video_data.get('statsV2')
                    data = {
                        'tiktok_video_id': tiktok_video_id,
                        'author_id': video_data.get('author', {}).get('id'),
                        'AIGCDescription': video_data.get('AIGCDescription'),
                        'CategoryType': video_data.get('CategoryType'),
                        'backendSourceEventTracking': video_data.get('backendSourceEventTracking'),
                        'collected': video_data.get('collected'),
                        'createTime': video_data.get('createTime'),
                        'video_desc': video_data.get('desc'),
                        'digged': video_data.get('digged'),
                        'diversificationId': video_data.get('diversificationId'),
                        'duetDisplay': video_data.get('duetDisplay'),
                        'duetEnabled': video_data.get('duetEnabled'),
                        'forFriend': video_data.get('forFriend'),
                        'itemCommentStatus': video_data.get('itemCommentStatus'),
                        'officalItem': video_data.get('officalItem'),
                        'originalItem': video_data.get('originalItem'),
                        'privateItem': video_data.get('privateItem'),
                        'secret': video_data.get('secret'),
                        'shareEnabled': video_data.get('shareEnabled'),
                        'stitchDisplay': video_data.get('stitchDisplay'),
                        'stitchEnabled': video_data.get('stitchEnabled'),
                        'can_repost': video_data.get('itemControl', {}).get('can_repost'),
                        'collectCount': video_status.get('collectCount'),
                        'commentCount': video_status.get('commentCount'),
                        'diggCount': video_status.get('diggCount'),
                        'playCount': video_status.get('playCount'),
                        'repostCount': video_status.get('repostCount'),
                        'shareCount': video_status.get('shareCount'),
                        'updated_at': func.now()
                    }

                    existing_video = await session.get(TikTokVideoDetails, tiktok_video_id)

                    if existing_video:
                        for key, value in data.items():
                            setattr(existing_video, key, value)
                        await session.commit()
                    else:
                        new_video = TikTokVideoDetails(**data)
                        session.add(new_video)
                        await session.commit()

            except Exception as e:
                await session.rollback()
                Globals.logger.error(f"Error occurred while inserting/updating TikTok video details: {e}", self.user)

    async def get_available_proxy(self):
        async with Globals.get_available_proxy_lock:
            async with AsyncSessionLocal() as session:
                try:
                    query = select(ProxyUrl).where(
                        ProxyUrl.is_using == False,
                        ProxyUrl.avg_delay > 0
                    ).order_by(ProxyUrl.fail_count.asc(), ProxyUrl.avg_delay.asc())
                    
                    proxies = (await session.execute(query)).scalars().all()
                    if not proxies:
                        return None

                    selected_proxy = proxies[0]

                    selected_proxy.is_using = True
                    await session.commit()

                    Globals.logger.debug(f"Selected proxy: {selected_proxy.current_port}", self.user)
                    return {
                        'id': selected_proxy.id,
                        'current_port': selected_proxy.current_port
                    }
                except Exception as e:
                    Globals.logger.error(f"Error occurred while fetching available proxy: {e}", self.user)
                    return None

    async def set_proxy_in_use(self, proxy_id, is_using: bool):
        async with AsyncSessionLocal() as session:
            try:
                proxy = await session.get(ProxyUrl, proxy_id)
                if proxy:
                    proxy.is_using = is_using
                    await session.commit()
            except Exception as e:
                Globals.logger.error(f"Error occurred while updating proxy is_using: {e}", self.user)

    async def increase_proxy_success(self, proxy_id):
        async with AsyncSessionLocal() as session:
            try:
                proxy = await session.get(ProxyUrl, proxy_id)
                if proxy:
                    proxy.success_count += 1
                    await session.commit()
            except Exception as e:
                Globals.logger.error(f"Error occurred while increasing proxy success count: {e}", self.user)

    async def increase_proxy_fail(self, proxy_id):
        async with AsyncSessionLocal() as session:
            try:
                proxy = await session.get(ProxyUrl, proxy_id)
                if proxy:
                    proxy.fail_count += 1
                    await session.commit()
            except Exception as e:
                Globals.logger.error(f"Error occurred while increasing proxy fail count: {e}", self.user)

    async def set_comments(self, tiktok_account, comments):
        async with AsyncSessionLocal() as session:
            try:
                account = await session.get(TikTokAccount, tiktok_account)
                if account:
                    account.comments = comments
                    account.updated_at = func.now()
                    await session.commit()
                else:
                    new_account = TikTokAccount(tiktok_account=tiktok_account, comments=comments)
                    session.add(new_account)
                    await session.commit()
            except Exception as e:
                Globals.logger.error(f"Error occurred while updating comments: {e}", self.user)