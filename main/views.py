import os

from django.shortcuts import render
import csv
from bs4 import BeautifulSoup as bs
import requests
import re
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

# Create your views here.
from problem_recommand.settings import BASE_DIR


def main(request):
    return render(
        request,
        'main.html'
    )


def learning(request):
    global problem_sim
    problem_sim = init()
    # 학습 러닝
    return render(
        request,
        'main.html'
    )


def search(request, user_id):
    problems = getProblems(user_id)
    problem_list = []
    for index in problems:
        print(index)
        tempProblems = get_recommand_problem(problem_sim, index)
        print(type(tempProblems))
        if tempProblems is not None:
            for i in range(len(tempProblems)):
                rank = tempProblems.iat[i, 2] // 5
                val = (tempProblems.iat[i, 2]) % 5
                if rank == 0:
                    level = '브론즈'
                elif rank == 1:
                    level = '실버'
                elif rank == 2:
                    level = '골드'
                elif rank == 3:
                    level = '플래티넘'
                elif rank == 4:
                    level = '다이아'
                else:
                    level = '루비'

                if val == 0:
                    level += '5'
                else:
                    level += str(6-val)
                problem = Problem_class(tempProblems.iat[i, 1],
                                        tempProblems.iat[i, tempProblems.shape[1]-1],
                                        level)
                problem_list.append(problem)
    problem_list.sort(key= lambda x: x.problemLevel)
    # 25개 중에 5개 고르기



    return render(
        request,
        'result.html',
        {
            'problemList': problem_list[:10]
        }
    )


class Problem_class:
    def __init__(self, problemId, problemLevel, problemLevelString):
        self.problemId = problemId
        self.problemLevel = problemLevel
        self.problemLevelString = problemLevelString


# class 하나로 합치기
def DataCrawl(userId):
    lists = []
    crawling_url = 'https://www.acmicpc.net/user/'
    crawling_url = crawling_url + userId
    response = requests.get(crawling_url, headers={'User-Agent': 'Mozilla/5.0'})
    text = response.text

    status = response.status_code;
    if (status >= 400 | status < 500):
        return None

    soup = bs(text, "html.parser")
    user_Detail = soup.find_all('div', {'class': 'panel panel-default'})
    cnt = 0  # panel panel-default가 여러개 존재하므로, 맞춘 문제(2번째) 항목 판별
    for user in user_Detail:
        if (cnt == 1):
            solved_Detail = soup.find('div', {'class': 'problem-list'})
            if (not solved_Detail):
                break
            solved = solved_Detail.find_all("a")
            for i in solved:
                href = i.attrs['href']
                href = re.sub('/problem/', '', href)
                lists.append(href)

            return lists
        else:
            cnt = cnt + 1


def getProblems(userId):
    # User 검색 후 맞춘 문제 리스트로 출력

    userSolved_list = DataCrawl(userId)

    if userSolved_list == None:
        return None
    else:
        hand = open(BASE_DIR + '/data/problemDetail.csv')
        problem = pd.read_csv(hand)
        dic = {}
        for i in range(len(problem)):
            dic[problem['problemId'][i]] = problem['level'][i]

        problems = {}
        for i in userSolved_list:
            data = dic.get(int(i))
            if data is not None:
                problems[i] = data

        problems = list(zip(problems.values(), problems.keys()))
        problems.sort(key=lambda x: (-x[0], x[1]))
        problem_list = []

        for i in range(len(problems)):
            if i == 5:
                break
            problem_list.append(int(problems[i][1]))

        print(problem_list)
        return problem_list


from sklearn.cluster import KMeans

from sklearn.metrics.pairwise import cosine_similarity


def init():
    # 문제에 대한 정보
    problem = pd.read_csv('data/tag_key.csv')
    user = pd.read_csv('data/userSolved.csv')
    user.columns = ['userId', 'problemId']

    # 데이터 중복행 삭제
    problem = problem.drop_duplicates()
    # K-Means를 하기 위해 문제 아이디를 제거
    problem_no = problem.iloc[:, 1:]

    k = 30
    model = KMeans(n_clusters=k, random_state=10)
    model.fit(problem_no)

    # Cluseter의 결과를 저장
    problem['cluster'] = model.fit_predict(problem_no)

    problem.to_csv("data/clusterProblem.csv")

    # 사용자와 문제정보를 병합
    user_problem = pd.merge(user, problem, on="problemId")

    # 사용자와 문제에 대한 피벗 테이블을 생성
    user_problem_pi = user_problem.pivot_table('cluster', index='problemId', columns='userId')

    # 백준에는 있지만 Solved ac에는 없는 문제를 -1로 태깅
    user_problem_pi.fillna(-1, inplace=True)

    # 문제간의 유사도를 구해 새로운 matiricx생성
    return cosine_similarity(user_problem_pi, user_problem_pi).argsort()[:, ::-1]


def Cal_distance(result, target_index):
    problem = pd.read_csv('data/clusterProblem.csv')
    problem = problem.drop_duplicates()
    sorter = []
    for i in range(len(result)):
        sorter.append(pow(result.iat[i, 2] - problem.iat[target_index, 2], 2))
    result.insert(len(result.columns), 'sorter', sorter, True)
    return result


def get_recommand_problem(problem_sim, problemId, top=30):
    problem = pd.read_csv('data/clusterProblem.csv')

    target_problem_index = problem[problem['problemId'] == problemId].index.values

    if (target_problem_index != None):
        # 코사인 유사도중 비슷한 코사인 유사도를 가진 정보를 뽑아낸다.
        sim_index = problem_sim[target_problem_index, :top].reshape(-1)
        # 본인 제외
        sim_index = sim_index[sim_index != target_problem_index]

        result = problem.iloc[sim_index]
        result = Cal_distance(result, target_problem_index[0])
        result = result.sort_values('sorter')[:10]
        result.to_csv('data/test.csv')
        return result
