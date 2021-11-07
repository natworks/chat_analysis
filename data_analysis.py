import re
import requests
import numpy as np
import pandas as pd
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw,ImageFont

import emoji
import plotly
import streamlit as st
import plotly.express as px

import data_cleaning
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator

def display_signal_analysis(chat_data: pd.DataFrame):
    pass

def get_date(row_idx, chat_data):
    date = datetime.strptime("{}:{} {} {} {}".format(
        chat_data.iloc[row_idx, chat_data.columns.get_loc("hour_of_day")],
        chat_data.iloc[row_idx, chat_data.columns.get_loc("minute_of_hour")],
        chat_data.iloc[row_idx, chat_data.columns.get_loc("day_of_month")],
        chat_data.iloc[row_idx, chat_data.columns.get_loc("month")],
        chat_data.iloc[row_idx, chat_data.columns.get_loc("year")]
    ), "%H:%M %d %b %Y")
    return date

def get_quietest_interval(chat_data):
    deltas = [0]
    previous_date = get_date(0, chat_data)

    for i in range(1, chat_data.shape[0]):
        current_date = get_date(i, chat_data)
        deltas.append((current_date - previous_date).total_seconds())
        previous_date = current_date

    quiest_interval = max(deltas)
    return deltas.index(quiest_interval), quiest_interval

def convert_seconds(seconds):
    day = int(seconds // (24 * 3600))
    time = seconds % (24 * 3600)
    hour = int(time // 3600)
    time %= 3600
    minutes = int(time // 60)
    time %= 60
    seconds = int(time)
   
    if day > 0:
        return "{} days {} hours and {} minutes".format(day, hour, minutes)
    elif hour > 0:
        return "{} hours and {} minutes".format(hour, minutes)
    elif minutes > 0:
        return "{} minutes".format(minutes)
    else:
        return "{} seconds".format(seconds)


def display_msg_gap(chat_data: pd.DataFrame):

    daily_average = chat_data.shape[0]//365
    quiest_interval_id, delta_in_seconds = get_quietest_interval(chat_data)
    formatted_time = convert_seconds(delta_in_seconds)
    interval_start = '{} of {}'.format(
        chat_data.iloc[quiest_interval_id-1, chat_data.columns.get_loc("day_of_month")],
        chat_data.iloc[quiest_interval_id-1, chat_data.columns.get_loc("month")],
        )
    interval_end = '{} of {}'.format(
        chat_data.iloc[quiest_interval_id, chat_data.columns.get_loc("day_of_month")],
        chat_data.iloc[quiest_interval_id, chat_data.columns.get_loc("month")],
        )

    

    st.write("That is an average of {} messages per day! The longest period without messages was {}. It happened between {} and {}.".format(
            daily_average,
            formatted_time,
            interval_start,
            interval_end
        ))

    # st.image("./imgs/rookie_numbers.jpg", caption='Meme Pump Numbers')
    st.text("")

def display_num_of_messages(chat_data: pd.DataFrame):
    """
    Biggest Message block   
    """
    msg_count = chat_data["author"].value_counts().to_frame()
    msg_count.reset_index(inplace=True)
    msg_count.columns = ['Author', 'Count']
    total_msgs = msg_count['Count'].sum()

    st.markdown(f'<span style="font-size: 24px;">In 2021, you group has sent a total of {total_msgs:,} messages. Here is everyone\'s contributions:</span>', unsafe_allow_html=True)
    st.text("")

    fig = px.bar(msg_count, y='Count', x='Author', text='Count', color="Count",
             color_continuous_scale=plotly.colors.sequential.Sunset)
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside', showlegend=False) #, marker_coloraxis=None)
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide',  plot_bgcolor='rgb(255,255, 255)', coloraxis_showscale=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgb(220,220,220)')
    st.plotly_chart(fig, use_container_width=True)


def get_freq_plot(data, column, column_renamed, sorting_order):
    msg_count = data[column].value_counts().to_frame()
    msg_count.reset_index(inplace=True)
    msg_count.columns = [column_renamed, 'Messages']

    fig = px.bar(msg_count, y='Messages', x=column_renamed)
    
    return fig, msg_count.iloc[0,0]

def display_time_info(chat_data: pd.DataFrame):
    month_chat, top_month  = get_freq_plot(chat_data, 'month', 'Month', ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    day_chat, top_day = get_freq_plot(chat_data, 'weekday', 'Weekday',["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    hour_chat, top_hour = get_freq_plot(chat_data, 'hour_of_day', 'Hour of Day', ['{:02d}'.format(t) for t in range(24)])

    st.subheader("The Busiest...")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Month of the year is:", top_month, None)
        st.plotly_chart(month_chat, use_container_width=True)
    with col2:
        st.metric("Day of the week is:", top_day, None)
        st.plotly_chart(day_chat, use_container_width=True)
    with col3:
        st.metric("Hour of the day is:", f"{top_hour}:00hr", None)
        st.plotly_chart(hour_chat, use_container_width=True)

def display_favourite_emojis(chat_data: pd.DataFrame):
    text = " ".join(str(msg) for msg in chat_data.body)
    all_emojis = "".join(word for word in text if emoji.is_emoji(word))

    unique_emojis = list(set(all_emojis))
    emoji_count = []

    for emoj in unique_emojis:
        count = all_emojis.count(emoj)
        emoji_count.append(count)

    arg_sorted = np.argsort(emoji_count, )[::-1]

    st.subheader("Your group's favourite emojis:")

    [col1, col2, col3, col4, col5] = st.columns(5)

    for i, col in enumerate([col1, col2, col3, col4, col5]):
        col.markdown(f'<span style="font-size: 72px;">{unique_emojis[arg_sorted[i]]}</span>', unsafe_allow_html=True)

def display_biggest_spammer(chat_data: pd.DataFrame):
    author_names, _ = data_cleaning.get_users(chat_data)
    links_per_user = []
    favourite_site = []
    
    for author in author_names:
        author_msgs = chat_data[chat_data["author"]==author]
        author_msgs_list = " ".join(str(msg) for msg in author_msgs.body)
        websites = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', author_msgs_list)
        unique_websites = list(set(websites))
        links_per_user.append(len(websites))
        if len(websites) > 0:
            counts = [
                websites.count(site) for site in unique_websites
            ]
            sorted_idx = np.argsort(counts, )[::-1]
            favourite_site.append([unique_websites[sorted_idx[0]], counts[sorted_idx[0]]])
        else:
            favourite_site.append([0, 0])

    idx_spammer = links_per_user.index(max(links_per_user))
    spammer = author_names[idx_spammer]
    
    st.markdown(f'<span style="font-size: 56px;">{spammer}</span> is the biggest spammer in your group.\
        Their favourite source is {favourite_site[idx_spammer][0]}. In fact, they have shared this website alone {favourite_site[idx_spammer][1]} times in 2021.', unsafe_allow_html=True)

    st.image("./imgs/awkward.png", caption='awkward..')

def split_sentence(input_phrase, char_per_line=22):
    sentences = ""
    text = ''
    all_words = input_phrase.split(' ')
#     print(all_words)
    start = 0
    complete = False
    while not complete:
        text = ''
#         print(start, 'sentences: ', sentences)
        for idx in range(start, len(all_words)):
            tmp_text = text + all_words[idx]
#             print(idx, tmp_text, len(tmp_text))
            if len(tmp_text) > char_per_line:
                start = idx
                sentences += f'{text}\n'
                break
            else:
                text += f'{all_words[idx]} '
                start = idx

#         print('bottom', start, text, len(text))
        if start == len(all_words) - 1 and len(tmp_text) < char_per_line:
            sentences += f'{text}\n'
            complete = True
            
    return sentences


def display_quote(chat_data: pd.DataFrame):
    count = 0
    images = {}
    
    url = f"https://api.unsplash.com/photos/random/?topics=='nature'&count=3&orientation=landscape&client_id={YOUR_ACCESS_KEY}"
    
    r = requests.get(url) #, data=token_data, headers=token_headers)
    token_response_data = r.json()

    font = ImageFont.truetype("./fonts/philosopher/Philosopher-BoldItalic.ttf", 36, encoding='unic')
    
    while count < 3:
        i = np.random.randint(0, chat_data.shape[0], size=1)[0]
        txt = "'{}'".format(chat_data.iloc[i, chat_data.columns.get_loc("body")])
        author = chat_data.iloc[i, chat_data.columns.get_loc("author")]
        
        if 5< len(txt) < 200 and 'kkk' not in txt and 'haha' not in txt and 'http' not in txt and 'gif' not in txt and 'GIF' not in txt and 'vídeo' not in txt \
            and 'video' not in txt and 'image' not in txt and 'audio' not in txt and '‎áudio' not in txt:
            print(txt)
            
            response = requests.get(token_response_data[count]['urls']['raw'] + "&w=600")
            images[count] = Image.open(BytesIO(response.content))
            
            d = ImageDraw.Draw(images[count])
            width, height = images[count].size
            
            sentences = split_sentence(txt,char_per_line=26)
            
            d.multiline_text((int(width*0.1),int(height*0.15)), "{}".format(sentences), font=font, fill=(255, 255, 255))
            d.multiline_text((int(width*0.55),int(height*0.8)), "-{}".format(author), font=font, fill=(255, 255, 255))
            count += 1

    st.subheader("Here are some messages to remember:")
    for i in range(3):
        st.image(images[i], caption='Original Image by: {} ({}) from Unsplash'.format(
            token_response_data[i]['user']['name'],
            token_response_data[i]['user']['links']['html'].split('/')[-1],
        ))

def handle_signal_media(chat_data: pd.DataFrame):
    author_names, _ = data_cleaning.get_users(chat_data)
    gifs_per_author = []
    audios_per_author = []


    for author in author_names:
        author_msgs = chat_data[chat_data["author"]==author]
        author_msgs_list = " ".join(str(msg) for msg in author_msgs.body)
        gifs = re.findall('image/gif', author_msgs_list)
        audios = re.findall('audio/aac', author_msgs_list)
        videos = re.findall('video/mp4', author_msgs_list)
        gifs_per_author.append(len(gifs) + len(videos))
        audios_per_author.append(len(audios))

    idx_gif_spammer = gifs_per_author.index(max(gifs_per_author))
    gif_person = author_names[idx_gif_spammer]

    idx_audio_spammer = audios_per_author.index(max(audios_per_author))
    audio_person = author_names[idx_audio_spammer]
    
    st.markdown(f'Sharing gifs is a skill that <span style="font-size: 56px;">{gif_person}</span> has certaily mastered, having shared {max(gifs_per_author)} gifs this year - more than anyone else in the group.', unsafe_allow_html=True)
    fig = px.pie(pd.DataFrame.from_dict({"authors": author_names, "media": gifs_per_author}),
             values='media', names='authors', color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig, use_container_width=True)
    st.text("")
    st.markdown(f'<span style="font-size: 56px;">{audio_person}</span> is almost a podcast host. They have shared the most audios this year. Don\'t forget to like and subscribe!', unsafe_allow_html=True)
    fig = px.pie(pd.DataFrame.from_dict({"authors": author_names, "media": audios_per_author}),
             values='media', names='authors', color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig, use_container_width=True)

def handle_android_media(chat_data: pd.DataFrame):
    author_names, _ = data_cleaning.get_users(chat_data)
    media_per_author = []


    for author in author_names:
        author_msgs = chat_data[chat_data["author"]==author]
        author_msgs_list = " ".join(str(msg) for msg in author_msgs.body)
        media = re.findall('Media omitted', author_msgs_list)
        media_per_author.append(len(media))

    idx_media_spammer = media_per_author.index(max(media_per_author))
    media_person = author_names[idx_media_spammer]
    
    st.markdown(f'<span style="font-size: 56px;">{media_person}</span> is just sitting there sharing audios and gifs. They have sent a whopping {max(media_per_author)} messages containing media this year.', unsafe_allow_html=True)
    fig = px.pie(pd.DataFrame.from_dict({"authors": author_names, "media": media_per_author}),
             values='media', names='authors', color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig, use_container_width=True)

def handle_iphone_media(chat_data: pd.DataFrame):
    author_names, _ = data_cleaning.get_users(chat_data)
    gifs_per_author = []
    audios_per_author = []

    for author in author_names:
        author_msgs = chat_data[chat_data["author"]==author]
        author_msgs_list = " ".join(str(msg) for msg in author_msgs.body)
        gifs = re.findall('GIF omitido', author_msgs_list)
        audios = re.findall('áudio ocultado', author_msgs_list)
        gifs_per_author.append(len(gifs))
        audios_per_author.append(len(audios))

    idx_gif_spammer = gifs_per_author.index(max(gifs_per_author))
    gif_person = author_names[idx_gif_spammer]

    idx_audio_spammer = audios_per_author.index(max(audios_per_author))
    audio_person = author_names[idx_audio_spammer]
    
    st.markdown(f'Sharing gifs is a skill that <span style="font-size: 56px;">{gif_person}</span> has certaily mastered, having shared {max(gifs_per_author)} gifs this year - more than anyone else in the group.', unsafe_allow_html=True)
    fig = px.pie(pd.DataFrame.from_dict({"authors": author_names, "media": gifs_per_author}),
             values='media', names='authors', color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig, use_container_width=True)
    st.text("")
    st.markdown(f'<span style="font-size: 56px;">{audio_person}</span> is almost a podcast host. They have shared {max(audios_per_author)} audios this year. Don\'t forget to like and subscribe!', unsafe_allow_html=True)
    fig = px.pie(pd.DataFrame.from_dict({"authors": author_names, "media": audios_per_author}),
             values='media', names='authors', color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig, use_container_width=True)

def display_media_person(chat_data: pd.DataFrame, input_source: str):
    if input_source == 'signal':
        handle_signal_media(chat_data)
    elif input_source == 'android':
        handle_android_media(chat_data)
    else:
        handle_iphone_media(chat_data)

    