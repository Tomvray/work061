import psycopg2
import pandas as pd

"""This module provides a Database class for connecting to psql patents database and execute queroies"""

class Database:
    def __init__(self, host, port, database, user, password):
        self.connection = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print("Database connection established.")


    def execute_query(self, query):
        """Execute a query and return the results fetchall()"""
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    ### Patent claims
    def get_claims(self, patent_id):
        """RETURN ALL CLAIMS FOR A GIVEN PATENT ID ordered by claim number"""
        query = f"SELECT claim_text FROM claims WHERE patent_id = '{patent_id}' ORDER BY claim_number"
        return self.execute_query(query)
    
    def get_claims_str(self, patent_id):
        """RETURN ALL CLAIMS FOR A GIVEN PATENT ID ordered by claim number as a single string"""

        query = f"SELECT claim_text, claim_number FROM claims WHERE patent_id = '{patent_id}' ORDER BY claim_number"
        claims = self.execute_query(query)
        
        #Protect if claims 1 is missing, return None
        if claims[0][1] != 1 and claims[0][1] != 0:
            return None
        return "\n".join([claim[0] for claim in claims])
    
    def get_claims_ids(self):
        """return all patent IDs that have claims in the database"""

        query = f"SELECT distinct patent_id FROM claims"
        ids = self.execute_query(query)
        return [id[0] for id in ids]

    #### Applications
    def get_application_ids(self):
        """return list of all application IDs in the database"""
    
        df = pd.read_csv("database/list_apps.csv")
        #convert app_id column to string
        df["app_id"] = df["app_id"].astype(str)
        return df["app_id"].tolist()

    def get_application_ids_year(self, year):
        """return list of all application IDs in the database for a given year"""
    
        df = pd.read_csv("database/list_apps.csv")
        df_year = df[df["year"] == year]
        print("types of app_id and year columns:", df_year["app_id"].dtype, df_year["year"].dtype)
        return df_year["app_id"].tolist()

    ### Office actions
    def get_patents_cited(self, app_id):
        
        query = f"SELECT parsed FROM citations WHERE app_id = '{app_id}'"
        return self.execute_query(query)

    def get_app_citations(self):
        """return list of all application IDs that have citations in the database"""
    
        query = f"SELECT distinct app_id FROM citations"
        ids = self.execute_query(query)
        return [id[0] for id in ids]
    
    def get_clean_citations(self):
        """return the pairs that have a citations and applications in the database"""
        #return a dic with app_id as key and list of cited patents as value for all app_ids that have citations and applications in the database

        query = f"SELECT app_id, parsed FROM citations WHERE app_id IN (SELECT app_id FROM applications) AND parsed IN (SELECT patent_id FROM claims) group by app_id, parsed"
        
        results = self.execute_query(query)
        clean_citations = {}
        for app_id, cited_patent in results:
            if app_id not in clean_citations:
                clean_citations[app_id] = []
            clean_citations[app_id].append(cited_patent)
        return clean_citations

    def get_clean_102_citations(self):
        """return the pairs that have a citations and applications in the database restricted to 102 rejections"""
        #return a dic with app_id as key and list of cited patents as value for all app_ids that have citations and applications in the database

        query = f"SELECT app_id, parsed FROM citations WHERE app_id IN (SELECT app_id FROM applications) AND parsed IN (SELECT patent_id FROM claims) AND app_id in (SELECT app_id FROM office_actions WHERE rejection_102=true) group by app_id, parsed"
        
        results = self.execute_query(query)
        clean_citations = {}
        for app_id, cited_patent in results:
            if app_id not in clean_citations:
                clean_citations[app_id] = []
            clean_citations[app_id].append(cited_patent)
        return clean_citations

    def get_clean_103_citations(self):
        """return the pairs that have a citations and applications in the database restricted to 102 rejections"""
        #return a dic with app_id as key and list of cited patents as value for all app_ids that have citations and applications in the database

        query = f"SELECT app_id, parsed FROM citations WHERE app_id IN (SELECT app_id FROM applications) AND parsed IN (SELECT patent_id FROM claims) AND app_id in (SELECT app_id FROM office_actions WHERE rejection_103=true) group by app_id, parsed"
        
        results = self.execute_query(query)
        clean_citations = {}
        for app_id, cited_patent in results:
            if app_id not in clean_citations:
                clean_citations[app_id] = []
            clean_citations[app_id].append(cited_patent)
        return clean_citations

    def close(self):
        self.connection.close()


if __name__ == "__main__":
    db = Database(
        host="db",
        port=5432,
        database="patents_db",
        user="postgres",
        password="postgres"
    )
    print(db.get_claims_str('7864457'))
    db.close()