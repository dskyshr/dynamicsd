from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from django.views.generic import TemplateView
from .forms import(
    ConditionsForm,
)
import math, random, statistics
import datetime
import pprint     # debug時のリスト・辞書確認用
import time       # debug時のsleep用
import csv

from .mylib import mymodule as mm


# TOP
## session操作時は複雑なので、クラスビューではなく関数ビューを使う
def TopView(request):
    template_name = './top/top.html'
    result = ""
    pp = pprint.PrettyPrinter(indent=4) # debug用

    o_max = 20;            # 最大選択肢数
    o_max_available = 20   # 1期あたりの選択可能クラス数(≒実質class数/4)
    o_limit = 3;           # 1期あたり申告数上限

    #o_max = 5;           # debug
    #o_max_available = 5  # debug

    utils = { # 獲得利得
       0 : 3, # 第1希望
       1 : 2, # 第2希望
       2 : 1, # 第3希望
    }

    # クラス情報初期化
    classes = {}

    if request.method == 'GET':
        # セッションに入力途中のデータがあればそれを使う。
        form = ConditionsForm(request.session.get('conditions_form_data'))
    else:
        # POST
        form = ConditionsForm(request.POST)
        if form.is_valid():
            #post = form.save(commit=False)
            # セッションに入力データを格納
            request.session['conditions_form_data'] = request.POST

            participants = int(request.POST['participants'])
            initial_dist = int(request.POST['initial_dist'])
            t            = int(request.POST['term'])
            mechanism    = int(request.POST['mechanism'])
            csv_req      = request.POST.get('csv',)
            csv_write_mode = int(request.POST['csv_write_mode'])
            csv_path     = './top/log/result.csv'
            #print(csv_req)
            #print(csv_write_mode)

            if   mechanism == 1 : mechanism_name = '複合優先順序メカニズム'
            elif mechanism == 2 : mechanism_name = '確率的ボストンメカニズム'

            # クラスは各期何が開催されるかわからないのでo_maxのなかからランダムにo_max_available個抽出
            classes = mm.set_current_classes(o_max, o_max_available)
            #pp.pprint(classes)

            # 学生の初期状態を構築
            students = {}
            for index in range(participants):

               # x値を基準化
               x = (o_max / participants) * index

               # 初期選択肢分布から自分の初期選択肢数を得る
               if   initial_dist == 1 : # ①線形型
                  options = -x + o_max
               elif initial_dist == 2 : # ②凸型
                  options = -math.sqrt(pow(o_max,2) - pow((x - o_max),2)) + o_max
               elif initial_dist == 3 : # ③凹型
                  options = math.sqrt(pow(o_max,2) - pow(x,2))

               # 選択肢数の小数点以下切り上げ
               options = math.ceil(options)

               # 選択肢数が申告数上限未満なら選好数も選択肢数
               his_o_limit = o_limit
               if options < his_o_limit :
                  his_o_limit = options

               # 学生の初期選好を構築
               preference = random.sample(list(classes.keys()), k=his_o_limit) # 要素をランダムにhis_o_limit個抽出(重複なし)
               #pp.pprint(preference)

               students[index] = {     # keyがstudent_id
                 'student_id'   : index, # 並べ替え用に入れておく
                 'options'      : options,
                 'start_term'   : 0,
                 #'end_term'    : '',
                 'preference'   : preference,
                 'allocated'    : [],
                 'text_credits' : 0,
                 'utils'        : 0,
               }

               # クラス情報に申告学生を格納
               #pp.pprint(students[index]['preference'])
               if len(students[index]['preference']) >= 1:
                  classes[students[index]['preference'][0]]['declared'][0].append(index) # 第0希望
               if len(students[index]['preference']) >= 2:
                  classes[students[index]['preference'][1]]['declared'][1].append(index) # 第1希望
               if len(students[index]['preference']) >= 3:
                  classes[students[index]['preference'][2]]['declared'][2].append(index) # 第2希望

            #pp.pprint(students)

            stats = {
               'exit'             : [], # 期別市場退出者数
               'exit_total'       : 0,  # 累計退出者数
               'total_term_dict'  : {}, # key=退出までの期間, value=人数
               'total_term_aly'   : [], # 退出までの期間の平均や分散計算用
               'utils'            : [], # 期別獲得利得
               'utils_total'      : 0,  # 累計獲得利得
               'total_utils_dict' : {}, # key=退出までの総利得, value=人数
               'total_utils_aly'  : [], # 利得の平均や分散計算用
            }

            # Matching Start ##################

            for i_t in range(t) :
               pp.pprint('<-- Processing ' + str(i_t) + 'th Term.... -------------------------------------------->')

               capacity_rem  = {}            # 残定員数初期化
               stats['exit'].insert(i_t, 0)  # 退出者数初期化
               stats['utils'].insert(i_t, 0) # 利得を初期化
               max_student_id = next(iter(reversed(students))) # 今期の学生の最大IDを取得しておく

               # 第1希望～第3希望
               for i_declared in range(3) : 
                    #pp.pprint('+---- ' + str(i_declared) + 'th preference. ---------------------------------------+')

                    for class_id in classes.keys() :
                       #pp.pprint('*------ Class No.' + str(class_id) +' ---------------------------------*')

                       # 定員チェック
                       # このクラスの残定員
                       if i_declared == 0 : # loop初回はMax定員数
                          capacity_rem[class_id] = classes[class_id]['capacity']
                       else :
                           if capacity_rem[class_id] == 0 :
                              #pp.pprint('class_id=' + str(class_id) + 'はすでに定員に達しています。')
                              continue # 次のクラスへ

                       # 第i_declared希望の学生idの配列
                       declared = classes[class_id]['declared'][i_declared]
                       #pp.pprint('class_id=' + str(class_id) + 'の残定員は'+ str(capacity_rem[class_id]) +'人:')
                       

                       if len(declared) >= 1 :
                          #pp.pprint('class_id=' + str(class_id)+'の第'+str(i_declared)+'希望者('+ str(len(declared)) +'人):')
                          #pp.pprint(classes[class_id]['declared'][i_declared])

                          # 希望者が定員以下のときは全員に割り当て
                          if  len(declared) <= capacity_rem[class_id] :
                             #pp.pprint('第'+str(i_declared)+'希望者が定員以下のため希望者全員に第'+str(i_declared)+'希望のクラスを割り当てます。')
                             

                             for i,student_id in enumerate(classes[class_id]['declared'][i_declared]) :
                                #pp.pprint('student_id:'+str(student_id)+'を処理中...')
                                
                                # 割り当てられたクラスを配列に記録
                                students[student_id]['allocated'].append(class_id)
                                
                                # 割り当てられたクラス以下のすべての申告情報を削除
                                if len(students[student_id]['preference']) > i_declared + 1 :
                                   for i_preference,el in enumerate(students[student_id]['preference']) :
                                      # ループの最初はスキップ
                                      if i_preference == 0 :
                                         continue;
                                      cancel_class_id = students[student_id]['preference'][i_preference]
                                      #pp.pprint(classes[cancel_class_id]['declared'][i_preference])
                                      classes[cancel_class_id]['declared'][i_preference].remove(student_id);
                                      #pp.pprint('student_id:' + str(student_id) + 'は割当済みのため第'+ str(i_preference) +'希望のクラスをキャンセルしました。')
                                      #pp.pprint(classes[cancel_class_id]['declared'][i_preference])
                                
                                # 利得を獲得
                                students[student_id]['utils'] += utils[i_declared]

                                #pp.pprint('student_id='+str(student_id))
                                students[student_id]['options'] -= 1 

                                # 選択肢が0になった学生は市場から退出
                                mm.leave_market(students, student_id, stats, i_t)

                             # 残定員を減算
                             capacity_rem[class_id] = capacity_rem[class_id] - len(declared)
                             if capacity_rem[class_id] == 0 :
                                #pp.pprint('class_id=' + str(class_id) + 'は定員に達したためマッチングを終了します。')
                                
                                continue # 次のクラスへ 

                          # 希望者が定員を超えていたら選択肢の少ない順から割り当て
                          else :
                             #pp.pprint('class_id=' + str(class_id) + 'の第' + str(i_declared) + '希望者が定員を超えています。')
                             # 複合優先順序メカニズム
                             if mechanism == 1 :
                                 
                                 #pp.pprint('希望者を選択肢の少ない順に優先します。優先順序のリストを作成します。')
                                 

                                 # 一時配列を作って申告学生を選択肢の少ない順にソート
                                 tmp_aly = []
                                 for i,student_id in enumerate(classes[class_id]['declared'][i_declared]) :
                                    tmp_aly.append(students[student_id])
                                 tmp_aly = (sorted(tmp_aly, key=lambda x: x['options'], reverse=False))
                                 #pp.pprint('第１希望のtmp_aly(class='+str(classes[class_id]['class_id'])+'):')
                                 #pp.pprint(tmp_aly)

                                 # 1番選択肢の少ない学生の選択肢数
                                 prev_options = tmp_aly[0]['options'] - 1
                                 # 選択肢数の同じ学生ごとにわける
                                 order_by_options = []
                                 i_order = -1
                                 for i_student,el in enumerate(tmp_aly) :
                                    if tmp_aly[i_student]['options'] == prev_options :
                                       order_by_options[i_order]['student_id'].append(tmp_aly[i_student]['student_id'])
                                    else :
                                       i_order += 1
                                       order_by_options.insert(i_order, {
                                          'options'    : tmp_aly[i_student]['options'],
                                          'student_id' : [tmp_aly[i_student]['student_id']]
                                       })
                                       prev_options = tmp_aly[i_student]['options']
                                 #pp.pprint(order_by_options)

                                 # 優先順序にしたがって希望者を割り当て
                                 for i_order,el in enumerate(order_by_options) :

                                    #pp.pprint('class_id=' + str(class_id) + 'の残りの定員は'+ str(capacity_rem[class_id]) +'人です')
                                    
                                    #pp.pprint('優先順序第'+ str(i_order) +'位の希望者は'+ str(len(order_by_options[i_order]['student_id'])) +'名です。')
                                    

                                    if capacity_rem[class_id] >= len(order_by_options[i_order]['student_id']) :
                                       #pp.pprint('優先順序第'+ str(i_order) +'位の希望者が定員以下のため全員にクラスを割り当てます。')
                                       

                                       for i,student_id in enumerate(order_by_options[i_order]['student_id']) :
                                          #pp.pprint(student_id)
                                          
                                          students[student_id]['allocated'].append(class_id)

                                          # 割り当てられたクラス以下のすべての申告情報を削除
                                          if len(students[student_id]['preference']) > i_declared + 1 :
                                             for i_preference,el in enumerate(students[student_id]['preference']) :
                                                # ループの最初はスキップ
                                                if i_preference == 0 :
                                                   continue;
                                                cancel_class_id = students[student_id]['preference'][i_preference]
                                                classes[cancel_class_id]['declared'][i_preference].remove(student_id);
                                                #pp.pprint('student_id:' + str(student_id) + 'は割当済みのため第'+ str(i_preference) +'希望のクラスをキャンセルしました。')

                                          # 利得を獲得
                                          students[student_id]['utils'] += utils[i_declared]

                                          students[student_id]['options'] -= 1 

                                          # 選択肢が0になった学生は市場から退出
                                          mm.leave_market(students, student_id, stats, i_t)

                                       # 残定員を減算
                                       capacity_rem[class_id] = capacity_rem[class_id] - len(order_by_options[i_order]['student_id'])
                                       if capacity_rem[class_id] == 0 :
                                          #pp.pprint('class_id=' + str(class_id) + 'は定員に達したためマッチングを終了します。')
                                          break # 次のクラスへ

                                    else :
                                       #pp.pprint('優先順序第'+ str(i_order) +'位の希望者が定員を超えています。')
                                       
                                       #pp.pprint('テキスト科目取得数の多い順に優先します。複優先順序のリストを作成します。')
                                       

                                       # テキスト科目取得数で順序を再構築
                                       # 一時配列を作って申告学生をテキスト科目取得数の多い順にソート
                                       tmp_aly = []
                                       for i,student_id in enumerate(order_by_options[i_order]['student_id']) :
                                          tmp_aly.append(students[student_id])
                                          tmp_aly = (sorted(tmp_aly, key=lambda x: x['text_credits'], reverse=True))
                                       #pp.pprint('第'+str(i_order)+'希望のtmp_aly(class='+str(classes[class_id]['class_id'])+'):')
                                       #pp.pprint(tmp_aly)

                                       # 1番テキスト科目取得数の多い学生の取得数
                                       prev_text_credits = tmp_aly[0]['text_credits'] - 1

                                       # テキスト取得数の同じ学生ごとにわける
                                       order_by_text_credits = []
                                       i_order = -1
                                       for i_student,el in enumerate(tmp_aly) :
                                          if tmp_aly[i_student]['text_credits'] == prev_text_credits :
                                             order_by_text_credits[i_order]['student_id'].append(tmp_aly[i_student]['student_id'])
                                          else :
                                             i_order += 1
                                             order_by_text_credits.insert(i_order, {
                                                'text_credits' : tmp_aly[i_student]['text_credits'],
                                                'student_id'   : [tmp_aly[i_student]['student_id']]
                                             })
                                             prev_text_credits = tmp_aly[i_student]['text_credits']
                                       #pp.pprint(order_by_text_credits)

                                       # 優先順序にしたがって希望者を割り当て
                                       for i_order,el in enumerate(order_by_text_credits) :

                                          #pp.pprint('class_id=' + str(class_id) + 'の残りの定員は'+ str(capacity_rem[class_id]) +'人です')
                                          #pp.pprint('複優先順序第'+ str(i_order) +'位の希望者は'+ str(len(order_by_text_credits[i_order]['student_id'])) +'名です。')

                                          if capacity_rem[class_id] >= len(order_by_text_credits[i_order]['student_id']) :
                                             #pp.pprint('複優先順序第'+ str(i_order) +'位の希望者が定員以下のため全員にクラスを割り当てます。')
                                             

                                             for i,student_id in enumerate(order_by_text_credits[i_order]['student_id']) :
                                                students[student_id]['allocated'].append(class_id)

                                                # 割り当てられたクラス以下のすべての申告情報を削除
                                                if len(students[student_id]['preference']) > i_declared + 1 :
                                                   for i_preference,el in enumerate(students[student_id]['preference']) :
                                                      # ループの最初はスキップ
                                                      if i_preference == 0 :
                                                         continue;
                                                      cancel_class_id = students[student_id]['preference'][i_preference]
                                                      classes[cancel_class_id]['declared'][i_preference].remove(student_id);
                                                      #pp.pprint('student_id:' + str(student_id) + 'は割当済みのため第'+ str(i_preference) +'希望のクラスをキャンセルしました。')

                                                # 利得を獲得
                                                students[student_id]['utils'] += utils[i_declared]

                                                students[student_id]['options'] -= 1 

                                                # 選択肢が0になった学生は市場から退出
                                                mm.leave_market(students, student_id, stats, i_t)

                                             # 残定員を減算
                                             capacity_rem[class_id] = capacity_rem[class_id] - len(order_by_text_credits[i_order]['student_id'])
                                             if capacity_rem[class_id] == 0 :
                                                #pp.pprint('class_id=' + str(class_id) + 'は定員に達したためマッチングを終了します。')
                                                break # 次のクラスへ

                                          else :
                                             #pp.pprint('複優先順序第'+ str(i_order) +'位の希望者が定員を超えています。抽選により決定します。')
                                             

                                             # 無作為に抽出したindexを得る)
                                             i_rand = mm.rand_ints_nodup(
                                                0, # 最小添え字は0
                                                len(order_by_text_credits[i_order]['student_id']) - 1, # 最大添え字は学生数-1
                                                capacity_rem[class_id]
                                             )
                                             #pp.pprint('当選者のindex:' + str(i_rand))
                                             

                                             # 抽選に当選した学生は選択肢-1,外れた学生は一定確率でテキスト科目単位を得る
                                             for i_student,student_id in enumerate(order_by_text_credits[i_order]['student_id']) :

                                                # 当選した学生
                                                if i_student in i_rand :
                                                   #pp.pprint('student_id:' + str(students[student_id]['student_id']) + 'が当選しました。')
                                                   students[student_id]['allocated'].append(class_id)

                                                   # 割り当てられたクラス以下のすべての申告情報を削除
                                                   if len(students[student_id]['preference']) > i_declared + 1 :
                                                      for i_preference,el in enumerate(students[student_id]['preference']) :
                                                         # ループの最初はスキップ
                                                         if i_preference == 0 :
                                                            continue;
                                                         cancel_class_id = students[student_id]['preference'][i_preference]
                                                         classes[cancel_class_id]['declared'][i_preference].remove(student_id);
                                                         #pp.pprint('student_id:' + str(student_id) + 'は割当済みのため第'+ str(i_preference) +'希望のクラスをキャンセルしました。')

                                                   # 利得を獲得
                                                   students[student_id]['utils'] += utils[i_declared]

                                                   students[student_id]['options'] -= 1 

                                                   # 選択肢が0になった学生は市場から退出
                                                   mm.leave_market(students, student_id, stats, i_t)

                                                # 外れた学生
                                                else :
                                                   #pp.pprint('student_id:' + str(students[student_id]['student_id']) + 'は当選しませんでした。')
                                                   #pp.pprint('現在第' + str(i_declared) + '希望')
                                                   #pp.pprint('選好の数:' + str(len(students[student_id]['preference'])))

                                                   # 次の希望がないとき
                                                   if len(students[student_id]['preference']) == (i_declared + 1) :
                                                      #pp.pprint('student_id:' + str(students[student_id]['student_id']) + 'は今期マッチできませんでした。')
                                                      # テキスト科目単位取得確率
                                                      #new_credit = [0]                    # 確率1で0を得る
                                                      new_credit = [1]                    # 確率1で1を得る
                                                      #new_credit = [2]                    # 確率1で2を得る
                                                      #new_credit = mm.rand_ints_nodup(0,1,1) # 確率1/2ずつで(0,1)を得る
                                                      #new_credit = rand_ints_nodup(0,2,1) # 確率1/3ずつで(0,1,2)を得る
                                                      #new_credit = rand_ints_nodup(0,3,1) # 確率1/4ずつで(0,1,2,3)を得る
                                                      students[student_id]['text_credits'] += new_credit[0]
                                                      #pp.pprint('student_id:' + str(students[student_id]['student_id']) + 'は、'+ str(new_credit[0]) +'個のテキスト科目を取得しました。')

                                             # 残定員を減算
                                             capacity_rem[class_id] = capacity_rem[class_id] - len(i_rand)

                                             if capacity_rem[class_id] == 0 :
                                                #pp.pprint('class_id=' + str(class_id) + 'は定員に達したためマッチングを終了します。')
                                                continue # 次のクラスへ

                                       if capacity_rem[class_id] == 0 :
                                          break # 次のクラスへ

                                # end 複合優先順序メカニズム

                             # LKC方式
                             elif mechanism == 2 :
                                #pp.pprint('抽選を行います。')

                                # 無作為に抽出したindexを得る)
                                i_rand = mm.rand_ints_nodup(
                                   0, # 最小添え字は0
                                   len(declared) - 1, # 最大添え字は学生数-1
                                   capacity_rem[class_id],
                                )
                                #pp.pprint('当選者のindex:' + str(i_rand))

                                for i_student,student_id in enumerate(classes[class_id]['declared'][i_declared]) :

                                   # 当選した学生の処理（外れた学生は何もしない）
                                   if i_student in i_rand :
                                      #pp.pprint('student_id:' + str(students[student_id]['student_id']) + 'が当選しました。')

                                      # 割り当てられたクラスを記録
                                      students[student_id]['allocated'].append(class_id)

                                      # 割り当てられたクラス以下のすべての申告情報を削除
                                      if len(students[student_id]['preference']) > i_declared + 1 :
                                         for i_preference,el in enumerate(students[student_id]['preference']) :
                                            # ループの最初はスキップ
                                            if i_preference == 0 :
                                               continue
                                            cancel_class_id = students[student_id]['preference'][i_preference]
                                            classes[cancel_class_id]['declared'][i_preference].remove(student_id);
                                            #pp.pprint('student_id:' + str(student_id) + 'は割当済みのため第'+ str(i_preference) +'希望のクラスをキャンセルしました。')

                                      # 利得を獲得
                                      students[student_id]['utils'] += utils[i_declared]

                                      students[student_id]['options'] -= 1 

                                      # 選択肢が0になった学生は市場から退出
                                      mm.leave_market(students, student_id, stats, i_t)

                                # 残定員を減算
                                capacity_rem[class_id] = capacity_rem[class_id] - len(i_rand)

                                if capacity_rem[class_id] == 0 :
                                   #pp.pprint('class_id=' + str(class_id) + 'は定員に達したためマッチングを終了します。')
                                   continue # 次のクラスへ
                             # end LKC方式

                       # debug時のみコメント解放
                       """
                       else :
                          #pp.pprint('class_id=' + str(class_id)+'の第'+str(i_declared)+'希望者はいません。')
                          
                       """

                       # 定員に達していたら次のクラスへ
                       if capacity_rem[class_id] == 0 :
                           continue

               #pp.pprint('第'+str(i_t)+'期の退出者: '+ str(stats['exit'][i_t]) +'名')
               #pp.pprint('累計退出者は'+ str(stats['exit_total']) +'名です。')
               

               # 次期があるとき
               if (i_t + 1) < t :

                  # Class情報を再構築
                  classes = mm.set_current_classes(o_max, o_max_available)
                  #pp.pprint(classes)

                  # 退出した数だけ新規参入者を追加
                  for index in range(stats['exit'][i_t]) :
                     students[max_student_id + index + 1] = { # keyは既存学生の最大IDの続きから
                       'student_id' : max_student_id + index + 1, 
                       'options'    : o_max, # 新規参入者は最大選択肢数を持つ
                       'start_term' : i_t + 1 ,
                       #'end_term'   : '',
                       'preference' : [],
                       'allocated'  : [],
                       'text_credits' : 0,
                       'utils'        : 0,
                     }
                  #pp.pprint(str(stats['exit'][i_t]) +'名の学生が市場に新規参入しました。')                 
                  #pp.pprint(students)

                  # 学生の選好を再構築
                  for student_id in students.keys() :

                     # 選択肢数が3未満なら選好数も3未満
                     his_o_limit = o_limit
                     if students[student_id]['options'] < his_o_limit :
                        his_o_limit = students[student_id]['options']

                     # 今期のクラスをランダムにhis_o_limit個抽出(重複なし)
                     #pp.pprint('student_id:' + str(student_id) + 'の選好 +++++++++++++++++++++++++++')
                     #pp.pprint('割り当て済みクラスは、')
                     #pp.pprint(students[student_id]['allocated'])
                     # key(class_id)だけを一旦コピー
                     classes_rem = list(classes.keys())
                     #pp.pprint(classes_rem)
                     for i,class_id in enumerate(students[student_id]['allocated']) :
                        if class_id in classes_rem :
                           classes_rem.remove(class_id)

                     #pp.pprint('割り当て済みクラスを除いたクラスは、、')
                     #pp.pprint(classes_rem)

                     # 今期選択可能なクラス数の上限が選好数の上限
                     if len(classes_rem) < his_o_limit :
                        his_o_limit = len(classes_rem)

                     # 選好を抽選
                     preference = random.sample(classes_rem, k=his_o_limit) 
                     #pp.pprint('今期の選好は、')
                     #pp.pprint(preference)

                     """
                     # 論理和判定で再抽選を繰り返す方法（効率悪い）
                     #pp.pprint('最初の抽選結果')
                     #pp.pprint(preference)
                     # 過去に割り当てられているクラスが含まれていたらもう一度
                     while any(x in students[student_id]['allocated'] for x in preference) : # 論理和で判定(1つでも含まれればTrue)
                        #pp.pprint('すでに割り当て済みのクラスがあるため再抽選')
                        preference = random.sample(list(classes.keys()), k=his_o_limit) 
                        #pp.pprint('再抽選結果')
                        #pp.pprint(preference)
                     """
                     students[student_id]['preference'] = preference

                     # クラス情報に申告学生を格納
                     if len(students[student_id]['preference']) >= 1:
                        classes[students[student_id]['preference'][0]]['declared'][0].append(student_id) # 第0希望
                     if len(students[student_id]['preference']) >= 2:
                        classes[students[student_id]['preference'][1]]['declared'][1].append(student_id) # 第1希望
                     if len(students[student_id]['preference']) >= 3:
                        classes[students[student_id]['preference'][2]]['declared'][2].append(student_id) # 第2希望
 
                  #pp.pprint(students)

            # 統計情報
            pp.pprint('===================================')
            pp.pprint('退出までの期間と人数は、')
            for total_term in stats['total_term_dict'].keys() :
               pp.pprint(str(total_term) + '期: ' + str(stats['total_term_dict'][total_term]) + '人')
            pp.pprint('===================================')
            pp.pprint('退出までの獲得利得と人数は、')
            for total_utils in stats['total_utils_dict'].keys() :
               pp.pprint(str(total_utils) + ': ' + str(stats['total_utils_dict'][total_utils]) + '人')
            pp.pprint('===================================')
            pp.pprint('使用メカニズム: ' + mechanism_name)
            pp.pprint('===================================')
            # 累計退出者数
            pp.pprint('累計退出者数: '+ str("{:,}".format(stats['exit_total'])) +'名')
            # 中央値を計算
            median = statistics.median(stats['total_term_aly'])
            pp.pprint('退出までの期間の中央値: '+'{:.0f}'.format(median) + '期')
            # 母分散を計算
            mean = statistics.mean(stats['total_term_aly'])
            pp.pprint('退出までの期間の平均: '+'{:.4f}'.format(mean) + '期')
            # 母分散を計算
            pvar = statistics.pvariance(stats['total_term_aly'])
            pp.pprint('退出までの期間の分散(母分散): '+'{:.4f}'.format(pvar))
            pp.pprint('===================================')
            # 累計獲得利得
            pp.pprint('累計獲得利得: '+ str("{:,}".format(stats['utils_total'])))
            # 中央値を計算
            median_u = statistics.median(stats['total_utils_aly'])
            pp.pprint('退出までの獲得利得の中央値: '+'{:.0f}'.format(median_u))
            # 母分散を計算
            mean_u = statistics.mean(stats['total_utils_aly'])
            pp.pprint('退出までの獲得利得の平均: '+'{:.4f}'.format(mean_u))
            # 母分散を計算
            pvar_u = statistics.pvariance(stats['total_utils_aly'])
            pp.pprint('退出までの獲得利得の分散(母分散): '+'{:.4f}'.format(pvar_u))
            pp.pprint('===================================')

            if csv_req :
               print(str("{:}".format(stats['exit_total'])) + ',' + '{:.0f}'.format(median) + ',' + '{:.4f}'.format(mean) + ',' +'{:.4f}'.format(pvar) + ',' + str("{:}".format(stats['utils_total'])) + ','+'{:.0f}'.format(median_u) + ',' + '{:.4f}'.format(mean_u) + ',' + '{:.4f}'.format(pvar_u))
               line = [
                 str("{:}".format(stats['exit_total'])), 
                 '{:.0f}'.format(median),
                 '{:.4f}'.format(mean),
                 '{:.4f}'.format(pvar) ,
                 str("{:}".format(stats['utils_total'])),
                 '{:.0f}'.format(median_u),
                 '{:.4f}'.format(mean_u),
                 '{:.4f}'.format(pvar_u)
               ]
               if   csv_write_mode == 1 : csv_write_mode = 'w' # 新規
               elif csv_write_mode == 2 : csv_write_mode = 'a' # 追記
               with open(csv_path, csv_write_mode, newline='') as f:
                  writer = csv.writer(f)
                  writer.writerow(line)

    pp.pprint('シミュレーション終了:' + str(datetime.datetime.now()))

        #    # 保存処理
        #    post.save()
        #    # メッセージ
        #    messages.info(request, f'タスクを開始しました。')
        #    # 保存したデータ取得
        #    tasktime_data = TaskTime.objects.filter(
        #        employee=request.user,
        #        status=1, # 1: 実行中
        #    ).latest('started_at')
        #    # update画面にリダイレクト
        #    return redirect('tasktime:update', pk=tasktime_data.id)
        #result = students

    context = {
        'form': form,
        'result_msg': 'シミュレーション終了 : ' + str(datetime.datetime.now()), 
    }
    return render(request, template_name, context)
