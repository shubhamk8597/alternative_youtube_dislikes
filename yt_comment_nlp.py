import json
from googleapiclient.discovery import build
import pandas as pd
import urllib.request
import urllib
from urllib.parse import urlparse, parse_qs
import streamlit as st
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import re
import matplotlib.pyplot as plt
from wordcloud import STOPWORDS, WordCloud
from config import api_key
import nltk
nltk.download('vader_lexicon')

## Vader Sentiment Analysis Polarity
sid = SentimentIntensityAnalyzer()

try:
    key = st.secrets['api_key'] 
except:
    key = api_key #replace with your youtube data api keys

def get_yt_video_id(url):
    """Returns Video_ID extracting from the given url of Youtube
    
    Examples of URLs:
      Valid:
        'http://youtu.be/_lOT2p_FCvA',
        'www.youtube.com/watch?v=_lOT2p_FCvA&feature=feedu',
        'http://www.youtube.com/embed/_lOT2p_FCvA',
        'http://www.youtube.com/v/_lOT2p_FCvA?version=3&amp;hl=en_US',
        'https://www.youtube.com/watch?v=rTHlyTphWP0&index=6&list=PLjeDyYvG6-40qawYNR4juzvSOg-ezZ2a6',
        'youtube.com/watch?v=_lOT2p_FCvA',
      
      Invalid:
        'youtu.be/watch?v=_lOT2p_FCvA',
    """
    if url.startswith(('youtu', 'www')):
        url = 'http://' + url
        
    query = urlparse(url)
    
    if 'youtube' in query.hostname:
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        elif query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    elif 'youtu.be' in query.hostname:
        return query.path[1:]
    else:
        raise ValueError

def build_service():
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"
    return build(YOUTUBE_API_SERVICE_NAME,
                 YOUTUBE_API_VERSION,
                 developerKey=key)

def clean_text(comment):
    '''Returens Clean text after removing special characters'''
    clean_text = ''
    #Step 1
    for i in comment:
        if i in ['%', '/', '\\', '#', '$', '^', '*', ':', '>', '<', '{', '}', '[', ']', '~', '|', '"', '=']:
            continue
        #check if its an ascii characters
        if ord(i) < 128 and ord(i) > 31:
            clean_text += i
        else:
            continue
    #Step 2       
    clean_text1 = re.sub(' +', ' ', clean_text)
    return clean_text1


def get_sentiment(comment):
    '''
    Uses Vader nltk lib to get the sentiment.
    Returns the sentiment value and type. positive, negative or neutral
    '''
    clean_comment = clean_text(comment)
    clean_comment = comment
    results= sid.polarity_scores(clean_comment)
    result = results['compound']
    if result >= 0.1:
        sentiment_type = 'POSITIVE'
    if result < 0:
        sentiment_type = 'NEGATIVE'
    if result >= 0 and result < 0.1:
        sentiment_type = 'NEUTRAL'
    return result,sentiment_type



#2 configure function parameters for required variables to pass to service
def get_comments_sentiment(videoId,part='snippet', 
                 maxResults=100, 
                 textFormat='plainText',
                 order='time'
                 ):

    #3 create empty lists to store desired information
    comments, commentsId, authorurls, authornames, repliesCount, likesCount, viewerRating, dates, vidIds, totalReplyCounts,vidTitles,sentiment,sentiment_types = [],[], [], [], [], [], [], [], [], [], [], [], []

    # build our service from path/to/apikey
    service = build_service()
    
    #4 make an API call using our service
    response = service.commentThreads().list(
        part=part,
        maxResults=maxResults,
        textFormat='plainText',
        order=order,
        videoId=videoId
        #allThreadsRelatedToChannelId=channelId
    ).execute()
    c = st.empty()
    a = 0
    while response: # this loop will continue to run until you max out your quota
        
        for item in response['items']:
            #5 index item for desired data features
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comment_id = item['snippet']['topLevelComment']['id']
            reply_count = item['snippet']['totalReplyCount']
            like_count = item['snippet']['topLevelComment']['snippet']['likeCount']
            authorurl = item['snippet']['topLevelComment']['snippet']['authorChannelUrl']
            authorname = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
            date = item['snippet']['topLevelComment']['snippet']['publishedAt']
            vidId = item['snippet']['topLevelComment']['snippet']['videoId']
            totalReplyCount = item['snippet']['totalReplyCount']
            vidTitle = get_vid_title(vidId)
            sentiment_value,sentiment_type = get_sentiment(comment)
            #6 append to lists
            comments.append(comment)
            commentsId.append(comment_id)
            repliesCount.append(reply_count)
            likesCount.append(like_count)
            authorurls.append(authorurl)
            authornames.append(authorname)
            dates.append(date)
            vidIds.append(vidId)
            totalReplyCounts.append(totalReplyCount)
            vidTitles.append(vidTitle)
            sentiment.append(sentiment_value)
            sentiment_types.append(sentiment_type)
            a = a +1
            c.subheader('Number of Comments analysed ' + str(a))
        
        try:
            if 'nextPageToken' in response:
                response = service.commentThreads().list(
                    part=part,
                    maxResults=maxResults,
                    textFormat=textFormat,
                    order=order,
                    videoId=videoId,
                    #allThreadsRelatedToChannelId=channelId,
                    pageToken=response['nextPageToken']
                ).execute()
            else:
                break
        except: break
    
    #9 return our data of interest
    return {
        'comment': comments,
        'comment_id': commentsId,
        'author_url': authorurls,
        'author_name': authornames,
        'reply_count' : repliesCount,
        'like_count' : likesCount,
        'date': dates,
        'vidid': vidIds,
        'total_reply_counts': totalReplyCounts,
        'vid_title': vidTitles,
        'sentiment':sentiment,
        'sentiment_type':sentiment_types
    }


# vidid to table name
def get_vid_title(vidid):
    params = {"format": "json", "url": "https://www.youtube.com/watch?v=%s" % vidid}
    url = "https://www.youtube.com/oembed"
    query_string = urllib.parse.urlencode(params)
    url = url + "?" + query_string

    with urllib.request.urlopen(url) as response:
        response_text = response.read()
        data = json.loads(response_text.decode())
        # print(data['title'])
        return data['title']

## Streamlite formating

st.set_option('deprecation.showPyplotGlobalUse', False)

st.title("No Dislikes? No Problem.Comments Don't Lie")
st.header('Enter the YouTube URL Link to get Insights')
st.write('Note- \n\n 1)Currently Supports only English Language Videos. \n\n 2)High number of comments(greater than 1000) will take more time. So sit back and relax')
url = st.text_input('')

if len(url) !=0:
    st.video(url)
    videoID = get_yt_video_id(url)
    video_comments_sentiment = get_comments_sentiment(videoID)
    df = pd.DataFrame(video_comments_sentiment)

    if len(df) == 0:
        st.header('Sorry,No comments to Analyse :(')
    else:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['just_date'] = df['date']

        cloud,pie = st.columns([1.5,2.5])
        

        ## Word Cloud
        word_cloud = ' '
        for i in range(len(df)):
            word_cloud = word_cloud + df['comment'][i]

        stopwords = STOPWORDS
        wc = WordCloud(background_color="white", stopwords=stopwords, height=500, width=300)
        wcloud=  wc.generate(word_cloud) 

        plt.imshow(wcloud, interpolation='bilinear')
        plt.axis("off")
        plt.show()
        with cloud:
            st.pyplot()


        ## Pie Chart

        df_sentiment = df['sentiment_type'].value_counts()
        label = df_sentiment.index.tolist()
        count = []
        colours_list = ['#43A640','#FFEE73','#F03333']
        colours = []
        for i in label:
            if i == 'POSITIVE':
                colours.append(colours_list[0])
            if i == 'NEUTRAL':
                colours.append(colours_list[1])
            if i == 'NEGATIVE':
                colours.append(colours_list[2])
        for i in df_sentiment:
            count.append(i)
        total = sum(count)
        fig1, ax1 = plt.subplots()
        ax1.pie(count, labels=label,colors=colours,autopct=lambda p: '{:.0f}'.format(p * total / 100),startangle=90)
        ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        with pie:
            st.pyplot(fig1)


        ##TOP POSITIVE

        top_positive = df.sort_values(by=['sentiment'],ascending=False).reset_index()
        top_positive = top_positive.drop(top_positive[top_positive.sentiment <= 0.1].index)
        if len(top_positive) == 0:
            st.header('TOP POSITIVE COMMENT')
            st.subheader('Nothing positive here')
        else:
            top_positive = top_positive[['author_name','comment']]
            top_positive = top_positive.head(1)
            st.header('TOP POSITIVE COMMENT')
            st.subheader('User')
            st.write(top_positive['author_name'][0])
            st.subheader('Comment')
            st.write(top_positive['comment'][0])

         ##TOP NEGATIVE

        top_negative = df.sort_values(by=['sentiment']).reset_index()
        top_negative = top_negative.drop(top_negative[top_negative.sentiment >= 0].index)
        if len(top_negative) == 0:
            st.header('TOP NEGATIVE COMMENT')
            st.subheader('Nothing negative here')
        else:
            top_negative = top_negative[['author_name','comment']]
            top_negative = top_negative.head(1)
            st.header('TOP NEGATIVE COMMENT')
            st.subheader('User')
            st.write(top_negative['author_name'][0])
            st.subheader('Comment')
            st.write(top_negative['comment'][0])

        ##LINE CHART
        df_sentiment_line = df[['sentiment']]
        st.header('Incomming Comments vs Sentiment')
        st.line_chart(df_sentiment_line)






