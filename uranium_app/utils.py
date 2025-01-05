# uranium_project\uranium_app\utils.py
from youtube_search import YoutubeSearch
import logging

def search_youtube_videos(query, max_results=10):
    """
    This function searches YouTube for videos based on a query
    and returns a list of dictionaries containing video details.
    
    Args:
    query (str): The search query to look for videos.
    max_results (int): The maximum number of results to return (default is 10).

    Returns:
    list: A list of dictionaries with video details.
    """
    # Perform the search and get results directly as a list
    search_results = YoutubeSearch(query, max_results=max_results).to_dict()

    video_list = []

    # Iterate over the results directly (since search_results is already a list)
    for video in search_results:
        video_info = {
            'title': video['title'],
            'link': f"https://www.youtube.com{video['url_suffix']}",
            'duration': video['duration'],
            'views': video['views'],
            'channel': video['channel'],
            'publish_time': video['publish_time']
        }
        video_list.append(video_info)

    return video_list



def get_youtube_videos():
    """
    This function returns a dictionary of YouTube videos categorized by type.
    
    Returns:
    dict: A dictionary with video categories as keys and lists of video details as values.
    """
    featured_videos = [
        "https://www.youtube.com/watch?v=BEfbBq-sofM",
        "https://www.youtube.com/watch?v=deO6rA1-GTY",
        "https://www.youtube.com/watch?v=SriP-LNQ62Q",
        "https://www.youtube.com/watch?v=Zqq3-ntaSvg",
        "https://www.youtube.com/watch?v=SxR__qarTCM",
        "https://www.youtube.com/watch?v=Cmzep3YaRNI"
    ]

    uranium_company_videos = [
        "https://www.youtube.com/watch?v=O9I_T3cOnG8",
        "https://www.youtube.com/watch?v=q8en645034k",
        "https://www.youtube.com/watch?v=-XQ474wpNW0",
        "https://www.youtube.com/watch?v=uMv9FsQvBPg",
        "https://www.youtube.com/watch?v=Fz1jWuf9elw",
        "https://www.youtube.com/watch?v=C4z7HaYU7jw",
        "https://youtu.be/ExPyjYoWGyw",
        "https://youtu.be/42vtRcv7K2I",
        "https://youtu.be/QhsNsQlKz-w",
        "https://www.youtube.com/watch?v=e4fsvzc8CCs",
        "https://www.youtube.com/watch?v=Mrl1Syzu7BU",
        "https://www.youtube.com/watch?v=GQxOydWEQ40",
        "https://www.youtube.com/watch?v=lSQkm_4sOgw",
        "https://www.youtube.com/watch?v=C4z7HaYU7jw",
        "https://www.youtube.com/watch?v=W_qIMLjMHW8",
        "https://www.youtube.com/watch?v=JRpTLaBhF-E"
    ]

    podcast_videos = [
        "https://www.youtube.com/watch?v=Riyoy3rifw4",
        "https://www.youtube.com/watch?v=eh3C9amkasI",
        "https://www.youtube.com/watch?v=YsXE5X1j3_I",
        "https://www.youtube.com/watch?v=_TYpITINcTg",
        "https://www.youtube.com/watch?v=RkrOJ8yQ5u4",
        "https://www.youtube.com/watch?v=BNzcCUkbY1g",
        "https://www.youtube.com/watch?v=7lnq369Kjo0",
        "https://www.youtube.com/watch?v=qapL6B5MgJQ",
        "https://www.youtube.com/watch?v=9D9n2gTSYMk",
        "https://www.youtube.com/watch?v=t4EJQPWjFj8",
        "https://www.youtube.com/watch?v=AXxNOmkSkgw",
        "https://www.youtube.com/watch?v=suXFKEN8mKM",
        "https://www.youtube.com/watch?v=2fyPYZXQrgo",
        "https://www.youtube.com/watch?v=q9QaWY3QOC4"
    ]

    education_videos = [
        "https://www.youtube.com/watch?v=NaPUdob0IWo",
        "https://www.youtube.com/watch?v=noxQTdYCJ3c",
        "https://www.youtube.com/watch?v=z8mUCBG49N8",
        "https://www.youtube.com/watch?v=yoQPLcam64g",
        "https://www.youtube.com/watch?v=0Ss02nkPKqQ",
        "https://www.youtube.com/watch?v=V94M_E7RuT0",
        "https://www.youtube.com/shorts/aunOQNDoQOM",
        "https://www.youtube.com/watch?v=pihVYaXphz8",
        "https://www.youtube.com/shorts/FspiwGDi1Cs",
        "https://www.youtube.com/watch?v=IVtwfSBSLtI",
        "https://www.youtube.com/watch?v=Cmzep3YaRNI",
        "https://www.youtube.com/watch?v=rd3sKqbiU1Q"
    ]

    shorts = [
        "https://www.youtube.com/watch?v=9r3YMgx-0OA",
        "https://www.youtube.com/watch?v=VKWZKptmCbA",
        "https://www.youtube.com/watch?v=U1g2aSj9ZTc",
        "https://www.youtube.com/watch?v=2W-GEE6YU4M",
        "https://www.youtube.com/watch?v=cijmokfb7qM",
        "https://www.youtube.com/watch?v=ldEy6UU8o4A"
    ]

    video_categories = {
        'featured': featured_videos,
        'uranium_company': uranium_company_videos,
        'podcast': podcast_videos,
        'education': education_videos,
        'shorts': shorts
    }

    all_videos = {}

    for category, video_urls in video_categories.items():
        video_list = []
        for url in video_urls:
            try:
                video_id = url.split('v=')[-1].split('&')[0]
                results = YoutubeSearch(video_id, max_results=1).to_dict()
                if results:
                    video_info = results[0]
                    video_list.append({
                        'title': video_info['title'],
                        'link': f"https://www.youtube.com{video_info['url_suffix']}",
                        'thumbnail': video_info['thumbnails'][0],
                        'duration': video_info['duration'],
                        'views': video_info['views'],
                        'channel': video_info['channel']
                    })
            except Exception as e:
                logger.error(f"Error fetching video info for {url}: {str(e)}")

        all_videos[category] = video_list

    return all_videos
