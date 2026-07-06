import logging
import datetime
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"


class ProductHuntClient:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _execute_query(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        if not self.token:
            raise ValueError("Product Hunt developer token is not configured.")

        logger.info(f"GRAPHQL QUERY:\n{query}")

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers=self.headers,
            )

            # Log rate limit headers
            limit = response.headers.get("x-rate-limit-limit")
            remaining = response.headers.get("x-rate-limit-remaining")
            reset = response.headers.get("x-rate-limit-reset")
            logger.info(f"PH Rate Limits - Limit: {limit}, Remaining: {remaining}, Reset: {reset}")

            if response.status_code == 401:
                raise ValueError("Unauthorized: Invalid Product Hunt developer token.")

            if response.status_code == 429:
                raise ValueError("Rate limit exceeded. Please try again later.")

            response.raise_for_status()

            result = response.json()
            if "errors" in result:
                error_msg = "; ".join([err.get("message", "Unknown error") for err in result["errors"]])
                raise ValueError(f"GraphQL Error: {error_msg}")

            return result

    def fetch_launches(self, sync_mode: str = "today", max_records: int = 100) -> List[Dict[str, Any]]:
        """
        Fetches launches (posts) from Product Hunt.
        sync_mode can be 'today' or 'recent_7_days'.

        The Product Hunt GraphQL schema defines:
          - Post.topics -> TopicConnection (has edges/node)
          - Post.makers -> [User!]!  (flat array, NO edges/node)
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        if sync_mode == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = now - datetime.timedelta(days=7)

        posted_after = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Query fields:
        #   - Post scalar fields accessed directly
        #   - Post.topics is TopicConnection -> edges { node { ... } }
        #   - Post.makers is [User!]! -> direct fields (NO edges/node)
        query = """
        query GetPosts($after: String, $postedAfter: DateTime) {
          posts(first: 20, after: $after, postedAfter: $postedAfter, order: VOTES) {
            edges {
              node {
                id
                name
                tagline
                description
                votesCount
                commentsCount
                createdAt
                featuredAt
                website
                url
                topics {
                  edges {
                    node {
                      id
                      name
                      slug
                    }
                  }
                }
                makers {
                  id
                  name
                  username
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """

        all_posts = []
        has_next_page = True
        after_cursor = None

        while has_next_page and len(all_posts) < max_records:
            variables = {
                "postedAfter": posted_after,
                "after": after_cursor,
            }
            try:
                result = self._execute_query(query, variables)
                posts_data = result.get("data", {}).get("posts", {})
                edges = posts_data.get("edges", [])

                for edge in edges:
                    node = edge.get("node")
                    if node:
                        all_posts.append(node)
                        if len(all_posts) >= max_records:
                            break

                page_info = posts_data.get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)
                after_cursor = page_info.get("endCursor")

                if not edges:
                    break

            except Exception as e:
                logger.error(f"Error fetching page: {str(e)}")
                raise e

        return all_posts
