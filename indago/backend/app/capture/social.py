"""
INDAGO Evidence Capture Platform
Social Media Capture Handlers
Supports: Instagram, Facebook, TikTok, YouTube, Twitter/X
"""
import asyncio
import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from app.forensics.logger import CaptureForensicLogger, ForensicEvent

logger = logging.getLogger(__name__)


def detect_platform(url: str) -> str:
    """Detect social media platform from URL."""
    domain = urlparse(url).netloc.lower()
    platform_map = {
        "instagram.com": "instagram",
        "www.instagram.com": "instagram",
        "facebook.com": "facebook",
        "www.facebook.com": "facebook",
        "fb.com": "facebook",
        "tiktok.com": "tiktok",
        "www.tiktok.com": "tiktok",
        "youtube.com": "youtube",
        "www.youtube.com": "youtube",
        "youtu.be": "youtube",
        "twitter.com": "twitter",
        "www.twitter.com": "twitter",
        "x.com": "twitter",
        "www.x.com": "twitter",
    }
    return platform_map.get(domain, "generic")


class SocialMediaExtractor:
    """
    Extract structured data from social media pages.
    Each platform has specific extraction logic.
    """

    def __init__(self, page, forensic_logger: CaptureForensicLogger):
        self.page = page
        self.forensic_logger = forensic_logger

    async def extract(self, url: str) -> dict:
        """Auto-detect platform and extract data."""
        platform = detect_platform(url)
        extractors = {
            "instagram": self.extract_instagram,
            "facebook": self.extract_facebook,
            "tiktok": self.extract_tiktok,
            "youtube": self.extract_youtube,
            "twitter": self.extract_twitter,
            "generic": self.extract_generic,
        }
        extractor = extractors.get(platform, self.extract_generic)
        data = await extractor(url)
        data["platform"] = platform
        data["extracted_at"] = datetime.now(timezone.utc).isoformat()

        self.forensic_logger.log(
            ForensicEvent.SOCIAL_DATA_EXTRACTED,
            f"Social media data extracted from {platform}",
            data={"platform": platform, "url": url, "has_data": bool(data)},
        )
        return data

    async def extract_twitter(self, url: str) -> dict:
        """Extract Twitter/X post data."""
        data = {}
        try:
            # Wait for tweet content
            await self.page.wait_for_selector('[data-testid="tweet"]', timeout=10000)

            data = await self.page.evaluate("""
                () => {
                    const tweets = document.querySelectorAll('[data-testid="tweet"]');
                    const main_tweet = tweets[0];
                    if (!main_tweet) return {};

                    const getText = (el, selector) => el?.querySelector(selector)?.textContent?.trim() || null;
                    const getAttr = (el, selector, attr) => el?.querySelector(selector)?.getAttribute(attr) || null;

                    // Extract main tweet
                    const tweet_text = getText(main_tweet, '[data-testid="tweetText"]');
                    const author = getText(main_tweet, '[data-testid="User-Name"]');
                    const time_el = main_tweet.querySelector('time');
                    const tweet_time = time_el?.getAttribute('datetime') || null;

                    // Metrics
                    const get_metric = (label) => {
                        const el = document.querySelector(`[data-testid="${label}"]`);
                        return el ? el.textContent.trim() : null;
                    };

                    // Hashtags
                    const hashtags = Array.from(main_tweet.querySelectorAll('a[href*="/hashtag/"]'))
                        .map(a => a.textContent.trim());

                    // Mentions
                    const mentions = Array.from(main_tweet.querySelectorAll('a[href^="/"]'))
                        .filter(a => a.textContent.startsWith('@'))
                        .map(a => a.textContent.trim());

                    // Images
                    const images = Array.from(main_tweet.querySelectorAll('img[src*="pbs.twimg.com"]'))
                        .map(i => i.src);

                    // Comments
                    const comments = Array.from(document.querySelectorAll('[data-testid="tweet"]'))
                        .slice(1, 50)
                        .map(t => ({
                            text: getText(t, '[data-testid="tweetText"]'),
                            author: getText(t, '[data-testid="User-Name"]'),
                            time: t.querySelector('time')?.getAttribute('datetime'),
                        }));

                    return {
                        post_text: tweet_text,
                        author_info: author,
                        post_datetime: tweet_time,
                        hashtags: hashtags,
                        mentions: mentions,
                        images: images,
                        comments: comments,
                        likes: get_metric('like'),
                        replies: get_metric('reply'),
                        retweets: get_metric('retweet'),
                    };
                }
            """)

            # Expand replies
            await self._expand_twitter_replies()

        except Exception as e:
            logger.warning(f"Twitter extraction partial: {e}")
            data["extraction_note"] = str(e)

        return data

    async def _expand_twitter_replies(self):
        """Expand Twitter/X reply threads."""
        try:
            for _ in range(5):
                show_more = await self.page.query_selector('[data-testid="cellInnerDiv"] button')
                if show_more:
                    await show_more.click()
                    await asyncio.sleep(1.5)
                else:
                    break
        except Exception:
            pass

    async def extract_instagram(self, url: str) -> dict:
        """Extract Instagram post data."""
        data = {}
        try:
            await self.page.wait_for_selector('article', timeout=10000)

            data = await self.page.evaluate("""
                () => {
                    const article = document.querySelector('article');
                    if (!article) return {};

                    // Caption
                    const caption_el = article.querySelector('h1') ||
                                      article.querySelector('[class*="Caption"]') ||
                                      article.querySelector('span[class]');
                    const caption = caption_el?.textContent?.trim() || null;

                    // Author
                    const author_el = article.querySelector('a[href*="/"]');
                    const author = author_el?.textContent?.trim() || null;

                    // Images
                    const images = Array.from(article.querySelectorAll('img'))
                        .map(i => ({ src: i.src, alt: i.alt }))
                        .filter(i => i.src && !i.src.includes('data:'));

                    // Videos
                    const videos = Array.from(article.querySelectorAll('video'))
                        .map(v => ({ src: v.src, poster: v.poster }));

                    // Likes
                    const likes_el = document.querySelector('section span');
                    const likes = likes_el?.textContent?.trim() || null;

                    // Hashtags from caption
                    const hashtags = caption ? (caption.match(/#[\\w]+/g) || []) : [];

                    // Time
                    const time_el = document.querySelector('time');
                    const post_time = time_el?.getAttribute('datetime') || null;

                    return {
                        post_text: caption,
                        author_username: author,
                        post_datetime: post_time,
                        hashtags: hashtags,
                        images: images,
                        videos: videos,
                        likes_text: likes,
                    };
                }
            """)

            # Extract comments
            data["comments"] = await self._extract_instagram_comments()

        except Exception as e:
            logger.warning(f"Instagram extraction partial: {e}")
            data["extraction_note"] = str(e)

        return data

    async def _extract_instagram_comments(self) -> list:
        """Extract and expand Instagram comments."""
        comments = []
        try:
            # Click load more comments buttons
            for _ in range(5):
                load_more = await self.page.query_selector('button:has-text("Load more comments")')
                if load_more:
                    await load_more.click()
                    await asyncio.sleep(1.5)
                else:
                    break

            comments = await self.page.evaluate("""
                () => {
                    const comment_els = document.querySelectorAll('article ul li[class]');
                    return Array.from(comment_els).slice(0, 200).map(c => ({
                        author: c.querySelector('a')?.textContent?.trim(),
                        text: c.querySelector('span')?.textContent?.trim(),
                        time: c.querySelector('time')?.getAttribute('datetime'),
                    })).filter(c => c.text);
                }
            """)
        except Exception:
            pass
        return comments

    async def extract_facebook(self, url: str) -> dict:
        """Extract Facebook post data."""
        data = {}
        try:
            await asyncio.sleep(3)  # Facebook needs extra load time

            data = await self.page.evaluate("""
                () => {
                    const getText = (selector) => document.querySelector(selector)?.textContent?.trim() || null;

                    // Post content
                    const post_content = getText('[data-ad-comet-preview="message"]') ||
                                        getText('[data-testid="post_message"]') ||
                                        getText('div[class*="story_body"]');

                    // Author
                    const author_el = document.querySelector('h3 strong a, [data-hovercard] a');
                    const author = author_el?.textContent?.trim() || null;

                    // Time
                    const time_el = document.querySelector('abbr[data-utime], time[datetime]');
                    const post_time = time_el?.getAttribute('data-utime') ||
                                     time_el?.getAttribute('datetime') || null;

                    // Images
                    const images = Array.from(document.querySelectorAll('img[src*="fbcdn.net"]'))
                        .map(i => i.src).slice(0, 20);

                    // Reactions
                    const reactions_el = document.querySelector('[aria-label*="reaction"]');
                    const reactions = reactions_el?.textContent?.trim() || null;

                    // Comments
                    const comments = Array.from(document.querySelectorAll('[aria-label="Comment"]'))
                        .slice(0, 100)
                        .map(c => ({ text: c.textContent?.trim() }));

                    return {
                        post_text: post_content,
                        author_username: author,
                        post_datetime: post_time,
                        images: images,
                        reactions_text: reactions,
                        comments: comments,
                    };
                }
            """)
        except Exception as e:
            logger.warning(f"Facebook extraction partial: {e}")
            data["extraction_note"] = str(e)

        return data

    async def extract_youtube(self, url: str) -> dict:
        """Extract YouTube video metadata."""
        data = {}
        try:
            await self.page.wait_for_selector('h1.ytd-video-primary-info-renderer', timeout=10000)

            data = await self.page.evaluate("""
                () => {
                    const getText = (selector) => document.querySelector(selector)?.textContent?.trim() || null;
                    const getAttr = (selector, attr) => document.querySelector(selector)?.getAttribute(attr) || null;

                    // Title
                    const title = getText('h1.ytd-video-primary-info-renderer') ||
                                 getText('h1[class*="title"]');

                    // Channel
                    const channel = getText('ytd-channel-name a') ||
                                   getText('#channel-name');

                    // Description
                    const description = getText('#description-text') ||
                                       getText('#description');

                    // Stats
                    const views = getText('.view-count') || getText('[class*="viewCount"]');
                    const likes = getText('[aria-label*="like"]');
                    const publish_date = getText('#info-strings yt-formatted-string') ||
                                        getText('.date');

                    // Tags
                    const tags = Array.from(document.querySelectorAll('meta[property="og:video:tag"]'))
                        .map(m => m.getAttribute('content'));

                    // Comments
                    const comments = Array.from(document.querySelectorAll('ytd-comment-renderer'))
                        .slice(0, 100)
                        .map(c => ({
                            author: c.querySelector('#author-text')?.textContent?.trim(),
                            text: c.querySelector('#content-text')?.textContent?.trim(),
                            likes: c.querySelector('#vote-count-middle')?.textContent?.trim(),
                            time: c.querySelector('.published-time-text')?.textContent?.trim(),
                        }));

                    return {
                        post_text: description,
                        title: title,
                        author_display_name: channel,
                        post_datetime: publish_date,
                        views_text: views,
                        likes_text: likes,
                        hashtags: tags,
                        comments: comments,
                    };
                }
            """)
        except Exception as e:
            logger.warning(f"YouTube extraction partial: {e}")
            data["extraction_note"] = str(e)

        return data

    async def extract_tiktok(self, url: str) -> dict:
        """Extract TikTok video metadata."""
        data = {}
        try:
            await asyncio.sleep(4)  # TikTok needs extra load time

            data = await self.page.evaluate("""
                () => {
                    const getText = (selector) => document.querySelector(selector)?.textContent?.trim() || null;

                    const description = getText('[class*="video-desc"]') ||
                                       getText('[data-e2e="browse-video-desc"]');

                    const author = getText('[class*="author-uniqueId"]') ||
                                  getText('[data-e2e="video-author-uniqueid"]');

                    const display_name = getText('[class*="author-nickname"]') ||
                                        getText('[data-e2e="video-author-nickname"]');

                    const likes = getText('[data-e2e="browse-like-count"]') ||
                                 getText('[class*="like-count"]');

                    const comments_count = getText('[data-e2e="browse-comment-count"]') ||
                                          getText('[class*="comment-count"]');

                    const shares = getText('[data-e2e="browse-share-count"]') ||
                                  getText('[class*="share-count"]');

                    const hashtags = (description || '').match(/#[\\w]+/g) || [];

                    const music = getText('[class*="music-title"]') ||
                                 getText('[data-e2e="video-music"]');

                    return {
                        post_text: description,
                        author_username: author,
                        author_display_name: display_name,
                        likes_text: likes,
                        comments_count_text: comments_count,
                        shares_text: shares,
                        hashtags: hashtags,
                        music: music,
                    };
                }
            """)
        except Exception as e:
            logger.warning(f"TikTok extraction partial: {e}")
            data["extraction_note"] = str(e)

        return data

    async def extract_generic(self, url: str) -> dict:
        """Generic extraction for unknown platforms."""
        try:
            return await self.page.evaluate("""
                () => ({
                    title: document.title,
                    description: document.querySelector('meta[name="description"]')?.getAttribute('content'),
                    og_title: document.querySelector('meta[property="og:title"]')?.getAttribute('content'),
                    og_description: document.querySelector('meta[property="og:description"]')?.getAttribute('content'),
                    og_image: document.querySelector('meta[property="og:image"]')?.getAttribute('content'),
                })
            """)
        except Exception:
            return {}
