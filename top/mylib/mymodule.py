import random
import pprint     # debug時のリスト・辞書確認用
pp = pprint.PrettyPrinter(indent=4)

# 重複なし乱数 ###########
#  a:最小の数
#  b:最大の数
#  k:抽出数
def rand_ints_nodup(a, b, k):
   ns = []
   if b < k : 
      k = b
   while len(ns) < k:
      n = random.randint(a, b)
      if not n in ns:
         ns.append(n)
   return ns

# 重複なし乱数(割り当て済みを除く) ##
# a:最小の数
# b:最大の数
# k: 抽出数
# e: 割り当て済みクラスIDリスト
def rand_ints_nodup_without_allocated(a, b, k, e):
   ns = []
   if b < k : 
      k = b
   while len(ns) < k:
      n = random.randint(a, b)
      if not n in ns and n not in e:
         ns.append(n)
   return ns

# クラス情報を構築 #############
def set_current_classes(o_max, o_max_available) :

   # 今期選択可能なクラスIDを抽選
   available_classes = []
   available_classes = rand_ints_nodup(0, o_max, o_max_available)

   # 当期のクラス情報をセット
   classes = {}
   for index in available_classes :
      if index == 38 :      # 英語R
         capacity = 130
      elif index == 39 :    # 英語W
         capacity = 110
      else :
         capacity = 100
      classes[index] = { # keyがclass_id
         'class_id' : index,    # 念のため入れておく
         'capacity' : capacity, # 定員数
         #'capacity' : 10,       # debug
         'declared' : [ [], [], [] ], # 第1～第3希望として申告した学生IDを格納する配列
      };

   return classes

# 市場退出、記録 #############
def leave_market(students, student_id, stats, i_t) :
   if students[student_id]['options'] == 0 :
      students[student_id]['end_term'] = i_t
      #pp.pprint('student_id:' + str(student_id) + 'が市場から退出しました。')
      #pp.pprint('student_id:' + str(student_id) + 'の退出までの獲得利得は'+str(students[student_id]['utils'])+'でした。')

      # 退出者数を記録
      stats['exit'][i_t]  += 1
      stats['exit_total'] += 1

      # 退出までの期間を記録
      total_term = (i_t + 1) - students[student_id]['start_term']
      if total_term in stats['total_term_dict'].keys() :
         stats['total_term_dict'][total_term] += 1
      else :
         stats['total_term_dict'][total_term] = 1
      stats['total_term_aly'].append(total_term)

      # 獲得利得を記録
      stats['utils'][i_t]  += students[student_id]['utils']
      stats['utils_total'] += students[student_id]['utils']

      # 退出までの獲得利得を記録
      if students[student_id]['utils'] in stats['total_utils_dict'].keys() :
         stats['total_utils_dict'][students[student_id]['utils']] += 1
      else :
         stats['total_utils_dict'][students[student_id]['utils']] = 1
      stats['total_utils_aly'].append(students[student_id]['utils'])


      # dictから削除
      students.pop(student_id)
