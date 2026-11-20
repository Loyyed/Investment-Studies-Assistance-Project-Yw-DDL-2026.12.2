"""Attach the deep case outputs to the same editable and offline album data."""
from pathlib import Path

from atlas_registry import read


def attach_cases(root, document):
    case_root=Path('docs/cases')
    if not (root/case_root/'model-acceptance.json').is_file():
        return document
    models={}
    for card in document['cards']:
        if not card['id'].startswith('company-'):
            continue
        code=card['id'].split('-')[1]
        model=read(root,case_root/code/'model.json')
        models[code]=model
        price=next(s for s in card['feature']['sections'] if s['id']=='price')
        price['chart']['series'][0]['values']=[
             model['cases'][k]['per_share'] for k in ('stress','base','improve')]+[model['close']]
        tests=model['tests']; raw=tests['matrix']
        xs=list(dict.fromkeys(r['x'] for r in raw))
        ys=list(dict.fromkeys(r['y'] for r in raw))
        roots=sum(len(r['roots']) for r in tests['boundary'])
        base=model['cases']['base']
        boundary=[]
        for r in tests['boundary']:
            actual=[p['recovered'] for p in r['roots']]
            x=[p['x'] for p in r['roots']]
            boundary.append([r['y'],r['low'],r['high'],r['value_low'],r['value_high'],
                             x,actual,r['status']])
        body=(
            f"{model['cutoff']} 收盘 {model['close']:.2f} {model['security']['quote']}。"
            f"独立从披露期实际、经营驱动、资本和权益输入得到基准 {base['per_share']:.2f}。"
            f"本表检验 {tests['x']} 与 {tests['y']}，在所列范围内可回代 {roots} 组解。"
            '\n\n'+tests['condition']
        )
        refs=[('案例正文',''),('模型、现金与权益','model.json'),('原件和行列','evidence-index.csv'),
              ('历年经营资本和现金','history.csv'),('近季与期末余额','interim.csv'),
              ('三条预测','forecast.csv'),('价格边界','reverse.csv'),('素材地图','report-map.md'),
              ('独立复核','independent-review.md')]
        card['feature']['sections'].append(dict(
            id='deepcase',title='从经营参数回到现价',body=body,
            annotation='图中各系列对应第二驱动的不同条件。价位单位为同日证券报价币种/股。',
            refs=[dict(title=n,href=f'/cases/{code}/{f}') for n,f in refs],
            tables=[dict(title='搜索端点与价格回代',columns=['第二驱动','搜索首端','搜索末端',
                    '首端每股','末端每股','解','回代每股','求解状态'],rows=boundary)],
            chart=dict(type='line',unit=model['security']['quote']+'/股',labels=[f'{x:.6g}' for x in xs],
                       series=[dict(name=f'{tests["y"]} {y:.6g}',values=[r['value'] for r in raw if r['y']==y]) for y in (ys if len(ys)<=5 else [ys[i] for i in (0,1,4,5,6)])]
                              +[dict(name='同日收盘',values=[model['close']]*len(xs))])
        ))
    valuation=next(c for c in document['cards'] if c['id']=='valuation')
    valuation['feature']['sections'].append(dict(id='deepcase-compare',title='五家公司同口径复算',
      annotation='',body='五家分别使用本地未复权收盘和各市场截点。管理层项目预计、期后版权利变化和证据缺项维持独立记录。',
      refs=[dict(title='选题比较与五家完整案例',href='/cases/')],
      tables=[dict(title='同一估值日的回代结果',columns=['代码','收盘','压力','基准','改善','报价币种','阶段17至新版差额'],
             rows=[[c,m['close'],*[m['cases'][k]['per_share'] for k in ('stress','base','improve')],
                    m['security']['quote'],sum(x['delta'] for x in m['stage17_to_case'])] for c,m in models.items()])]))
    return document
