import os

from supabase import create_client


class SupabaseClient:

    def __init__(self):

        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url:
            raise RuntimeError(
                "Variabile SUPABASE_URL non configurata"
            )

        if not key:
            raise RuntimeError(
                "Variabile SUPABASE_KEY non configurata"
            )

        self.client = create_client(url, key)

    # ============================================================
    # DOWNLOAD LOG
    # ============================================================

    def get_log(self, stagione, giornata):

        response = (
            self.client
            .table("download_logs")
            .select("*")
            .eq("stagione", stagione)
            .eq("giornata", giornata)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    def is_completed(self, stagione, giornata):

        log = self.get_log(stagione, giornata)

        if not log:
            return False

        return log.get("status") == "COMPLETED"

    def save_log(
        self,
        stagione,
        giornata,
        status,
        records_inserted=0,
        error_message=None,
    ):

        data = {
            "stagione": stagione,
            "giornata": giornata,
            "status": status,
            "records_inserted": records_inserted,
        }

        if error_message:
            data["error_message"] = str(error_message)

        (
            self.client
            .table("download_logs")
            .upsert(
                data,
                on_conflict="stagione,giornata",
            )
            .execute()
        )

    # ============================================================
    # STATS
    # ============================================================

    def insert_stats(self, records):

        if not records:
            return 0

        print(
            f"   💾 Inserimento Supabase: "
            f"{len(records)} record"
        )

        (
            self.client
            .table("player_stats_history")
            .upsert(
                records,
                on_conflict=(
                    "player_id,"
                    "stagione,"
                    "giornata,"
                    "redazione"
                ),
            )
            .execute()
        )

        return len(records)

    # ============================================================
    # NEXT DOWNLOAD
    # ============================================================

    def get_next_missing(self, seasons):

        for stagione in seasons:

            for giornata in range(1, 39):

                if not self.is_completed(
                    stagione,
                    giornata,
                ):
                    return stagione, giornata

        return None, None
