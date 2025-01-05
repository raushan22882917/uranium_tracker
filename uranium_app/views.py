# uranium_project\uranium_app\views.py

import asyncio
import base64
import hashlib
import json
import logging


import aiohttp
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.cache import cache
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.html import strip_tags
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from newspaper import Article
from asgiref.sync import sync_to_async
from asgiref.sync import async_to_sync
from goose3 import Goose

from .forms import ForumPostForm, ForumCommentForm, EmailSubscriptionForm
from .glossary_terms import GLOSSARY_TERMS
from .models import UraniumPrice, NewsArticle, Stock, ForumPost, ForumComment, EmailSubscription
from .serializers import RegisterSerializer
from .tasks import fetch_uranium_data_sync, get_article_content, fetch_stock_news, fetch_iaea_news
from .utils import search_youtube_videos


logger = logging.getLogger('uranium_app')

class HomeAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            logger.info("Fetching uranium data...")
            uranium_data = fetch_uranium_data_sync()
            logger.info("Uranium data fetched successfully")

            if uranium_data is None:
                logger.warning("Uranium data is None")
                return Response({'message': 'Unable to fetch uranium data at this time.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            spot_price = uranium_data.get('spot_price', 'N/A')
            logger.info(f"Spot price: {spot_price}")

            if 'chart_data' in uranium_data:
                uranium_data['chart_data'] = self.prepare_chart_data(uranium_data['chart_data'])

            stocks = uranium_data.get('stocks', {})
            
            if stocks is None:
                stocks = {}
            logger.info(f"Number of stocks fetched: {len(stocks)}")

            for symbol, stock_data in stocks.items():
                try:
                    if 'data' in stock_data and len(stock_data['data']) >= 2:
                        current_price = float(stock_data['data'][-1])
                        previous_price = float(stock_data['data'][-2])
                        change_1d = ((current_price - previous_price) / previous_price) * 100
                        stock_data['change_1d'] = change_1d
                    else:
                        stock_data['change_1d'] = None

                    for key in ['current_price', 'last_price', 'change_1m', 'change_1y', 'volume', 'market_cap']:
                        if isinstance(stock_data.get(key), str):
                            try:
                                stock_data[key] = float(stock_data[key])
                            except ValueError:
                                stock_data[key] = None
                except Exception as e:
                    logger.error(f"Error processing stock data for {symbol}: {str(e)}")
                    stock_data['change_1d'] = None

            most_followed_stocks = sorted(
                [(symbol, data) for symbol, data in stocks.items() if data.get('volume') is not None],
                key=lambda x: x[1]['volume'],
                reverse=True
            )[:5]
            logger.info(f"Number of most followed stocks: {len(most_followed_stocks)}")

            sorted_stocks = sorted(
                [(symbol, data) for symbol, data in stocks.items() if data.get('change_1d') is not None],
                key=lambda x: x[1]['change_1d'],
                reverse=True
            )
            logger.info(f"Number of sorted stocks: {len(sorted_stocks)}")

            top_gainers = sorted_stocks[:8]
            top_losers = sorted_stocks[-8:][::-1]
            logger.info(f"Number of top gainers: {len(top_gainers)}")
            logger.info(f"Number of top losers: {len(top_losers)}")

            stock_datas = []
            for ticker, info in stocks.items():
                stock_datas.append({
                    "ticker": "  " + ticker,
                    "current_price": info.get("current_price", None),
                    "change_1m": info.get("change_1m", None),
                })

            mining_tech_news = uranium_data.get('mining_technology_com_news', [])
            featured_news = mining_tech_news[:2] if mining_tech_news else None
            stock_news_data = uranium_data.get("stock_news")[:4]

            context = {
                "uranium_data": uranium_data,
                'uranium_spot_price': spot_price,
                'most_followed_stocks': most_followed_stocks,
                'top_gainers': top_gainers,
                'top_losers': top_losers,
                'stocks': stock_datas,
                "stock_news": stock_news_data[:4],
                "featured_news": featured_news
            }

            return Response(context, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in home view: {str(e)}", exc_info=True)
            return Response({'message': 'An error occurred while fetching uranium data.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def prepare_chart_data(self, chart_data):
        for chart_type in ['intraday', 'three_year']:
            if chart_type in chart_data and 'svg' in chart_data[chart_type]:
                chart_data[chart_type]['svg'] = chart_data[chart_type]['svg']
        return json.dumps(chart_data)


class NewsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            uranium_data = fetch_uranium_data_sync()

            mining_tech_news = uranium_data.get('mining_technology_com_news', [])
            inform_news = uranium_data.get('inform_kz_news', [])
            mining_com_news = uranium_data.get('mining_com_news', [])
            northern_miner_com_news = uranium_data.get('northern_miner_com_news', [])
            world_nuclear_news_com = uranium_data.get('world_nuclear_news_com', [])
            stock_news = uranium_data.get('stock_news', [])
            iaea_news = uranium_data.get('iaea_news', [])

            featured_news = mining_tech_news[0] if mining_tech_news else None

            context = {
                'featured_news': featured_news,
                'latest_news': (
                    mining_com_news[:3] +
                    world_nuclear_news_com[:3] +
                    mining_tech_news[:3] +
                    iaea_news[:3]
                ),
                'global_uranium_news': (
                    northern_miner_com_news[:2] +
                    world_nuclear_news_com[3:6] +
                    inform_news[:4]
                ),
                'stock_news': stock_news[:9]
            }

            return Response(context, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in news view: {str(e)}")
            return Response({'message': 'An error occurred while fetching news data.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NewsDetailAPIView(APIView):
    async def get(self, request, article_id, *args, **kwargs):
        try:
            uranium_data = fetch_uranium_data_sync()
            all_news = (
                uranium_data.get('mining_technology_com_news', []) +
                uranium_data.get('inform_kz_news', []) +
                uranium_data.get('mining_com_news', []) +
                uranium_data.get('northern_miner_com_news', []) +
                uranium_data.get('world_nuclear_news_com', []) +
                uranium_data.get('stock_news', [])
            )

            article = next((article for article in all_news if article['id'] == article_id), None)

            if article is None:
                logger.error(f"Article not found for ID: {article_id}")
                return Response({'error': 'Article not found'}, status=status.HTTP_404_NOT_FOUND)

            # Fetch the full article content
            article_content = await self.get_article_content(article['link'])
            article['full_content'] = article_content

            related_articles = [a for a in all_news if a['id'] != article_id][:4]

            context = {
                'article': article,
                'related_articles': related_articles
            }

            return Response(context, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in news_detail view: {str(e)}")
            return Response({'error': 'An error occurred while fetching the article.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def get_article_content(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    html = await response.text()

            # Try with newspaper3k first
            article = Article(url)
            article.set_html(html)
            article.parse()
            content = article.text
            
            # If content is empty, try with goose3
            if not content:
                g = Goose()
                article = g.extract(raw_html=html)
                content = article.cleaned_text
            
            return content
        except Exception as e:
            logger.error(f"Error fetching article content: {str(e)}")
            return "Failed to retrieve the article content."



    async def get_stock_article_content(self, url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    article_body = soup.find('div', {'class': 'caas-body'})
                    if article_body:
                        paragraphs = article_body.find_all('p')
                        return '\n\n'.join([p.get_text() for p in paragraphs])
                return "Failed to retrieve the article content."


class CalDataAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            uranium_data = fetch_uranium_data_sync()
            calendar_html = uranium_data.get('calendar', {}).get('calendar_html', '')
            event_data = uranium_data.get('calendar', {}).get('event_data', [])

            context = {
                'calendar_html': calendar_html,
                'event_data': event_data
            }
            return Response(context, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in cal_data view: {str(e)}", exc_info=True)
            return Response({'message': 'An error occurred while fetching calendar data.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WorldNuclearDataAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            logger.info("Fetching uranium data for world_nuclear_data view")
            uranium_data = fetch_uranium_data_sync()
            logger.info("Uranium data fetched successfully")
            
            nuclear_data = uranium_data.get('nuclear_data', {})
            
            if not nuclear_data:
                logger.warning("No nuclear data found in uranium_data")
                return Response({'message': 'Failed to retrieve nuclear data.'}, status=status.HTTP_404_NOT_FOUND)
            
            logger.debug(f"Nuclear data: {json.dumps(nuclear_data, indent=2)}")
            
            context = {'data': nuclear_data}
            return Response(context, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error in world_nuclear_data view: {e}", exc_info=True)
            return Response({'message': 'Failed to retrieve nuclear data.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StocksAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            logger.info("Fetching uranium data...")
            uranium_data = fetch_uranium_data_sync()
            logger.info(f"Uranium data fetched: {uranium_data is not None}")

            if uranium_data is None:
                logger.warning("Unable to fetch uranium data")
                return Response({'message': 'Unable to fetch data at this time.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            stocks_list = []  

            stocks = uranium_data.get('stocks', {})

            for key, value in stocks.items():
                
                stock_data = {
                    'ticker_name': key,
                    'company_name': value.get("name"),
                    'change_1m': value.get("change_1m"),
                    'current_price': value.get("current_price"),
                    'last_price': value.get("last_price"),
                    'change_1y': value.get("change_1y"),
                    'volume': value.get("volume"),
                    'market_cap': value.get("market_cap"),
                    'pe_ratio': value.get("pe_ratio")
                }

                stocks_list.append(stock_data)

            logger.info(f"Stocks data: {type(stocks)}, {len(stocks) if isinstance(stocks, dict) else 'Not a dict'}")

            if not isinstance(stocks, dict):
                logger.error(f"Unexpected stocks data type: {type(stocks)}")
                return Response({'message': 'Unexpected data format for stocks.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if not stocks:
                logger.warning("No stocks data found in uranium_data")
                return Response({'message': 'No stock data available.'}, status=status.HTTP_404_NOT_FOUND)

            total_stocks = len(stocks)
            prices = [float(stock['current_price']) for stock in stocks.values() if isinstance(stock, dict) and stock.get('current_price') and stock['current_price'] != 'N/A']
            average_price = sum(prices) / len(prices) if prices else 0
            total_market_cap = sum(float(stock['market_cap']) for stock in stocks.values() if isinstance(stock, dict) and stock.get('market_cap') and stock['market_cap'] != 'N/A')
            changes = [float(stock['change_1m']) for stock in stocks.values() if isinstance(stock, dict) and stock.get('change_1m') and stock['change_1m'] != 'N/A']
            average_1m_change = sum(changes) / len(changes) if changes else 0

            most_followed_stocks = sorted(
                [(symbol, data) for symbol, data in stocks.items() if data.get('volume') is not None],
                key=lambda x: x[1]['volume'],
                reverse=True
            )[:5]

            sorted_stocks = sorted(
                [(symbol, stock) for symbol, stock in stocks.items() if isinstance(stock, dict) and stock.get('change_1m') and stock['change_1m'] != 'N/A'],
                key=lambda x: float(x[1]['change_1m']),
                reverse=True
            )
            top_gainers = sorted_stocks[:5]
            top_losers = sorted_stocks[-5:]

            context = {
                'stocks': stocks_list,
                'uranium_spot_price': uranium_data.get('spot_price', 'N/A'),
                'total_stocks': total_stocks,
                'average_price': average_price,
                'total_market_cap': total_market_cap,
                'average_1m_change': average_1m_change,
                'top_performing_stocks': top_gainers,
                'top_losers': top_losers,
                'most_followed_stocks': most_followed_stocks,
            }
            logger.info(f"Context prepared: {list(context.keys())}")
            return Response(context, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error in stocks view: {str(e)}", exc_info=True)
            return Response({'message': f'An error occurred while fetching stock data: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetTopPerformingStocksAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            stocks_data = request.data.get('stocks_data', {})
            if not stocks_data:
                return Response({'message': 'Stocks data is missing.'}, status=status.HTTP_400_BAD_REQUEST)

            top_stocks = self.get_top_performing_stocks(stocks_data)
            return Response({'top_stocks': top_stocks}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in GetTopPerformingStocksAPIView: {str(e)}", exc_info=True)
            return Response({'message': 'An error occurred while processing stocks.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_top_performing_stocks(self, stocks_data):
        fields_to_normalize = ['change_1m', 'change_1y', 'pe_ratio', 'volume', 'market_cap']
        for field in fields_to_normalize:
            self.normalize_values(stocks_data, field)

        for stock in stocks_data.values():
            stock['performance_score'] = self.calculate_performance_score(stock)

        top_stocks = sorted(stocks_data.items(), key=lambda x: x[1].get('performance_score', 0), reverse=True)[:3]
        return top_stocks

    def normalize_values(self, stocks_data, field):
        try:
            values = [float(stock.get(field, 0)) for stock in stocks_data.values() if self.is_numeric(stock.get(field))]

            if not values:
                return

            min_value, max_value = min(values), max(values)
            if min_value == max_value:
                for stock in stocks_data.values():
                    stock[f'{field}_normalized'] = 0
            else:
                for stock in stocks_data.values():
                    if self.is_numeric(stock.get(field)):
                        stock[f'{field}_normalized'] = (float(stock.get(field, 0)) - min_value) / (max_value - min_value)
                    else:
                        stock[f'{field}_normalized'] = 0
        except Exception as e:
            logger.error(f"Error normalizing {field}: {str(e)}")

    def is_numeric(self, value):
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def calculate_performance_score(self, stock):
        return (stock.get('change_1m_normalized', 0) * 0.4 +
                stock.get('change_1y_normalized', 0) * 0.3 +
                stock.get('pe_ratio_normalized', 0) * 0.1 +
                stock.get('volume_normalized', 0) * 0.1 +
                stock.get('market_cap_normalized', 0) * 0.1)


class AboutAPIView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({'message': 'About this app'}, status=status.HTTP_200_OK)

class GlossaryAPIView(APIView):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').lower()
        if query:
            filtered_terms = [term for term in GLOSSARY_TERMS if query in term['term'].lower() or query in term['definition'].lower()]
        else:
            filtered_terms = GLOSSARY_TERMS

        return Response({'glossary_terms': filtered_terms}, status=status.HTTP_200_OK)


class EssentialsView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({'message': 'This is the essentials page.'}, status=status.HTTP_200_OK)


class ContactView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({'message': 'This is the contact page.'}, status=status.HTTP_200_OK)


class ForumAPIView(APIView):
    def get(self, request, *args, **kwargs):
        posts = ForumPost.objects.order_by('-created_at')
        return Response({'posts': list(posts.values())}, status=status.HTTP_200_OK)


class CreatePostAPIView(APIView):
    @login_required
    def post(self, request, *args, **kwargs):
        form = ForumPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return Response({'message': 'Post created successfully.'}, status=status.HTTP_201_CREATED)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailAPIView(APIView):
    @login_required
    def get(self, request, post_id, *args, **kwargs):
        try:
            post = ForumPost.objects.get(id=post_id)
        except ForumPost.DoesNotExist:
            raise Http404("Forum post not found")

        comments = post.comments.all()
        return Response({'post': post, 'comments': list(comments.values())}, status=status.HTTP_200_OK)

    @login_required
    def post(self, request, post_id, *args, **kwargs):
        try:
            post = ForumPost.objects.get(id=post_id)
        except ForumPost.DoesNotExist:
            raise Http404("Forum post not found")

        form = ForumCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return Response({'message': 'Comment added successfully.'}, status=status.HTTP_201_CREATED)

        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class RegisterAPIView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        return Response({'user': request.user.username}, status=status.HTTP_200_OK)


class SubscribeAPIView(APIView):
    def post(self, request, *args, **kwargs):
        form = EmailSubscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'You have successfully subscribed to our newsletter!')
            return Response({'message': 'Subscription successful.'}, status=status.HTTP_201_CREATED)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionListAPIView(APIView):
    def get(self, request, *args, **kwargs):
        subscriptions = EmailSubscription.objects.all()
        return Response({'subscriptions': list(subscriptions.values())}, status=status.HTTP_200_OK)


class SendEmailAPIView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        subject = "Your Subject Here"
        body = """
        Dear [Recipient Name],

        We are reaching out to provide you with an important update regarding the Uranium project. Please review the details below:

        [Insert your message content here.]

        Should you have any questions or require further assistance, please do not hesitate to contact us. We are here to support you.

        Thank you for your attention.
        """
        from_email = "raushan2288.jnvbanka@gmail.com"

        try:
            send_mail(subject, body, from_email, [email])
            messages.success(request, f'Email sent successfully to {email}')
            return Response({'message': f'Email sent to {email}'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {str(e)}")
            return Response({'message': f'Failed to send email to {email}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateAvatarAPIView(APIView):
    @login_required
    def post(self, request, *args, **kwargs):
        try:
            avatar_data = request.POST.get('avatar')
            if not avatar_data:
                return Response({'error': 'No avatar data received'}, status=status.HTTP_400_BAD_REQUEST)

            format, imgstr = avatar_data.split(';base64,')
            ext = format.split('/')[-1]
            filename = f'avatar_{request.user.id}.{ext}'
            data = ContentFile(base64.b64decode(imgstr), name=filename)
            request.user.avatar.save(filename, data, save=True)

            avatar_url = request.build_absolute_uri(request.user.avatar.url)

            return Response({'avatar_url': avatar_url}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error updating avatar: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAvatarAPIView(APIView):
    @csrf_exempt
    @login_required
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            if data.get('delete'):
                user = request.user
                user.avatar = '/static/avatars/default-avatar.png'
                user.save()
                return Response({'success': True}, status=status.HTTP_200_OK)
            return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error deleting avatar: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserLogoutAPIView(APIView):
    @require_http_methods(["GET", "POST"])
    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


class SearchQuestionsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        query = request.GET.get("q")
        if query:
            results = ForumPost.objects.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            ).distinct()
        else:
            results = ForumPost.objects.all()

        return Response({'posts': list(results.values())}, status=status.HTTP_200_OK)



class GetUraniumYoutubeVideos(APIView):
    """
    API View to fetch and return YouTube videos related to 'uranium news' with error handling.
    """

    def get(self, request):
        try:
            # Use the utility function to get uranium-related videos
            youtube_videos = search_youtube_videos("uranium news")

            # Check if any videos were found
            if not youtube_videos:
                logging.warning("No YouTube videos found for 'uranium news'")
                return Response({"error": "No videos found for the query"}, status=status.HTTP_404_NOT_FOUND)

            # Return the results as a JSON response
            return Response({"videos": youtube_videos}, status=status.HTTP_200_OK)

        except Exception as e:
            logging.error(f"Error occurred while fetching YouTube videos: {e}")
            return Response({"error": "An error occurred while fetching YouTube videos"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BaseNewsAPIView(APIView):
    def get_news_data(self, key):
        try:
            uranium_data = fetch_uranium_data_sync()  # Make sure this function is synchronous
            news_data = uranium_data.get(key, [])
            return news_data
        except Exception as e:
            logger.error(f"Error fetching {key}: {str(e)}")
            raise e

class MiningComNewsAPIView(BaseNewsAPIView):
    def get(self, request, *args, **kwargs):  # Make this a synchronous view
        try:
            news_data = self.get_news_data('mining_com_news')
            return Response({
                "data": news_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"An error occurred while fetching the data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NucNetNewsAPIView(BaseNewsAPIView):
    def get(self, request, *args, **kwargs):  # Make this a synchronous view
        try:
            news_data = self.get_news_data('nucnet_news')
            return Response({
                "data": news_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"An error occurred while fetching the data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WorldNuclearNewsAPIView(BaseNewsAPIView):
    def get(self, request, *args, **kwargs):
        try:
            news_data = self.get_news_data('world_nuclear_news_com')
            return Response({
                "data": news_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"An error occurred while fetching the data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MiningTechnologyNewsAPIView(BaseNewsAPIView):
    def get(self, request, *args, **kwargs):
        try:
            news_data = self.get_news_data('mining_technology_com_news')
            return Response({
                "data": news_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"An error occurred while fetching the data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InformKZNewsAPIView(BaseNewsAPIView):
    def get(self, request, *args, **kwargs):
        try:
            news_data = self.get_news_data('inform_kz_news')
            return Response({
                "data": news_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"An error occurred while fetching the data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StockNewsAPIView(BaseNewsAPIView):
    def get(self, request, *args, **kwargs):
        try:
            news_data = self.get_news_data('stock_news')
            return Response({
                "data": news_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"An error occurred while fetching the data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IAEANewsAPIView(BaseNewsAPIView):
    def get(self, request, *args, **kwargs):
        try:
            news_data = self.get_news_data('iaea_news')
            return Response({
                "data": news_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"An error occurred while fetching the data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class NorthernMinerNewsAPIView(BaseNewsAPIView):
    def get(self, request, *args, **kwargs):
        try:
            news_data = self.get_news_data('northern_miner_com_news')
            return Response({
                "data": news_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"An error occurred while fetching the data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ArticleContentAPIView(APIView):
    async def get(self, request, article_id, *args, **kwargs):

        try:
            uranium_data = fetch_uranium_data_sync()

            all_news = (
                uranium_data.get('mining_technology_com_news', []) +
                uranium_data.get('inform_kz_news', []) +
                uranium_data.get('mining_com_news', []) +
                uranium_data.get('northern_miner_com_news', []) +
                uranium_data.get('world_nuclear_news_com', []) +
                uranium_data.get('stock_news', [])
            )

            article = next((article for article in all_news if article['id'] == article_id), None)

            if article is None:
                return Response({'error': 'Article not found'}, status=status.HTTP_404_NOT_FOUND)

            article_content = await self.get_article_content(article['link'])

            response_data = {
                'id': article['id'],
                'title': article['title'],
                'publisher': article['publisher'],
                'published_date': article['published_date'],
                'content': article_content,
                'source_url': article['link']
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in article_content view: {str(e)}")
            return Response({'error': 'An error occurred while fetching the article content.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def get_article_content(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    html = await response.text()

            # Try with newspaper3k first
            article = Article(url)
            article.set_html(html)
            article.parse()
            content = article.text
            
            # If content is empty, try with goose3
            if not content:
                g = Goose()
                article = g.extract(raw_html=html)
                content = article.cleaned_text
            
            return content
        except Exception as e:
            logger.error(f"Error fetching article content: {str(e)}")
            return "Failed to retrieve the article content."


