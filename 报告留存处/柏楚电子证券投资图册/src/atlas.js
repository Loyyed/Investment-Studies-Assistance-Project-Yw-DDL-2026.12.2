
"use strict";
const D=JSON.parse(document.querySelector("#atlas-data").textContent);
const $=(selector,root=document)=>root.querySelector(selector), $$=(selector,root=document)=>Array.from(root.querySelectorAll(selector));
const enc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const f=(value,digits=2)=>value===""||value==null?"—":Number(value).toLocaleString("zh-CN",{minimumFractionDigits:digits,maximumFractionDigits:digits});
const signed=(value,digits=2)=>value>0?"+"+f(value,digits):f(value,digits).replace("-","−");
const pct=(value,digits=2)=>f(Number(value)*100,digits)+"%";
const n=(x,d=2)=>f(Number(x),d);
const palette=["#2a7963","#bd684d","#bd9250","#6182a3"];
const source=(file)=>"data/"+file;
const gh=(file)=>D.sourceRoot+file;
const link=(label,href)=>`<a href="${enc(href)}">${enc(label)}</a>`;
const links=items=>`<div class="linkrow">${items.map(([l,h])=>link(l,h)).join(" · ")}</div>`;
const out=(id,html)=>{$("#"+id).innerHTML=html};
const wrap=(id,title,caption,content)=>`<section class="panel" id="${id}"><h3>${title}</h3><p class="caption">${caption}</p>${content}</section>`;
const card=(title,value,sub="")=>`<div class="metric"><small>${title}</small><strong>${value}</strong><small>${sub}</small></div>`;
const detail=(title,body,id="")=>`<details ${id?'id="'+id+'"':""}><summary>${title}</summary>${body}</details>`;
const kv=(header,rows)=>`<div class="tableframe" tabindex="0" role="region" aria-label="可左右滚动的数据表"><table><thead><tr>${header.map(x=>"<th scope='col'>"+x+"</th>").join("")}</tr></thead><tbody>${rows.map(row=>"<tr>"+row.map(x=>"<td>"+x+"</td>").join("")+"</tr>").join("")}</tbody></table></div>`;
const raw=(label,file)=>link(label,source(file));
const plot=(id)=>`<div class="chart-wrap"><div class="chart" id="${id}"></div><div class="zoom-controls"><button type="button" data-zoom="${id}">放大图件</button></div></div>`;
const tabs=(id,items)=>`<div class="tabs" role="group" aria-label="${id}" id="${id}">${items.map(([key,name],i)=>`<button type="button" data-key="${key}" aria-pressed="${i===0}">${name}</button>`).join("")}</div>`;
function clickTabs(id,fn){
    const group=$("#"+id);
    group.addEventListener("click",e=>{
        const b=e.target.closest("[data-key]");
        if(!b)return;
        $$("button",group).forEach(x=>x.setAttribute("aria-pressed",String(x===b)));
        fn(b.dataset.key);
    });
}
const svg=(title,contents,w=720,h=275)=>`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${enc(title)}"><title>${enc(title)}</title>${contents}</svg>`;
const caption=(text)=>`<p class="meta">${text}</p>`;
function trend(title,unit,xs,series,config={}){
    const l=76,r=688,t=35,b=215;
    const xf=i=>l+i*(r-l)/Math.max(xs.length-1,1);
    const values=series.flatMap(s=>s.points.filter(v=>v!==null));
    let lo=config.lo??Math.min(0,...values), hi=config.hi??Math.max(...values)*1.09;
    const yf=y=>b-(y-lo)/(hi-lo||1)*(b-t);
    let markup="";
    for(let i=0;i<5;i++){
        const y=lo+(hi-lo)*i/4, at=yf(y);
        markup+=`<line class="grid" x1="${l}" y1="${at}" x2="${r}" y2="${at}"/><text class="axis" x="${l-7}" y="${at+5}" text-anchor="end">${n(y,config.digits??0)}</text>`;
    }
    markup+=`<text class="axis" x="${l}" y="23">${enc(unit)}</text>`;
    if(config.hatch){
        const end=(xf(1)+xf(2))/2;
        markup+=`<defs><pattern id="no-root-hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(40)"><line y2="9" stroke="#c39881" stroke-opacity=".65" stroke-width="3"/></pattern></defs><rect x="${l}" y="${t}" width="${end-l}" height="${b-t}" fill="url(#no-root-hatch)"/>`;
    }
    if(config.breakAt!==undefined){
        const at=xf(config.breakAt)-12;
        markup+=`<line x1="${at}" y1="${t}" x2="${at}" y2="${b}" stroke="#a68c6c" stroke-dasharray="4 5"/><text class="axis" x="${at+2}" y="${t+12}">${enc(config.breakLabel??"分类断点")}</text>`;
    }
    for(const s of series){
        const segments=[]; let current=[];
        s.points.forEach((v,i)=>{
            if(v===null){if(current.length)segments.push(current);current=[];}
            else current.push([i,v]);
        });
        if(current.length)segments.push(current);
        for(const segment of segments){
            markup+=`<polyline class="line" points="${segment.map(([i,v])=>xf(i)+","+yf(v)).join(" ")}" fill="none" stroke="${s.color}" stroke-width="3.5" stroke-dasharray="${s.dash??""}"/>`;
            for(const [i,value] of segment){
                const sel=(config.selected===i)?" is-current":"";
                markup+=`<circle class="point${sel}" cx="${xf(i)}" cy="${yf(value)}" r="${sel?7:5}" fill="${s.color}"><title>${enc(s.name+" "+xs[i]+" "+f(value,config.tipDigits??2))}</title></circle>`;
            }
        }
    }
    xs.forEach((x,i)=>{
        const anchor=i===0?"start":i===xs.length-1?"end":"middle";
        markup+=`<text class="axis" ${(i%2!==0&&i!==xs.length-1)?'data-dense="1"':""} x="${xf(i)}" y="240" text-anchor="${anchor}">${enc(x)}</text>`;
    });
    if(config.xLabel)markup+=`<text class="axis" x="${r}" y="265" text-anchor="end">${enc(config.xLabel)}</text>`;
    return svg(title,markup);
}
function waterfall(title,rows,unit,opts={}){
    const size=rows.length, l=73,r=690,t=37,b=193, slot=(r-l)/size, bw=Math.min(48,slot*.52);
    const limits=rows.flatMap(x=>[x.start,x.end]);
    let low=opts.low??Math.min(0,...limits), high=opts.high??Math.max(...limits)*1.05;
    const scale=y=>b-(y-low)/(high-low||1)*(b-t);
    let m=`<text class="axis" x="${l}" y="23">${unit}</text>`;
    for(let i=0;i<4;i++){
        const v=low+(high-low)*i/3, y=scale(v);
        m+=`<line class="grid" x1="${l}" x2="${r}" y1="${y}" y2="${y}"/><text class="axis" x="${l-6}" y="${y+4}" text-anchor="end">${f(v,opts.ticks??0)}</text>`;
    }
    rows.forEach((x,i)=>{
        if(opts.seen!==undefined&&i>=opts.seen)return;
        const at=l+slot*(i+.5), top=scale(Math.max(x.start,x.end)), bottom=scale(Math.min(x.start,x.end));
        const fill=x.total?"#437866":x.end>=x.start?"#73a88d":"#bb6a51";
        const value=x.total?f(x.value,opts.digits??2):signed(x.value,opts.digits??2);
        if(i<size-1)m+=`<path class="tick" d="M ${at+bw/2} ${scale(x.end)} H ${at+slot-bw/2}" stroke-dasharray="4 3"/>`;
        m+=`<rect x="${at-bw/2}" y="${top}" width="${bw}" height="${Math.max(2,bottom-top)}" rx="3" fill="${fill}"><title>${enc(x.label+" "+value)}</title></rect><text class="chart-label" x="${at}" y="${top-6}" text-anchor="middle">${value}</text><text class="axis" x="${at}" y="218" text-anchor="middle">${enc(x.short??x.label)}</text>`;
    });
    return svg(title,m,720,231);
}
function stepPlot(id,bar,title,rows,unit,opts={}){
    let seen=rows.length;
    out(bar,`<div class="actions"><button type="button" data-cmd="start">从首项看</button><button type="button" data-cmd="next">显示下一项</button><button type="button" data-cmd="all">显示全桥</button><small aria-live="polite"></small></div>`);
    const g=$("#"+bar);
    function draw(){
        out(id,waterfall(title,rows,unit,{...opts,seen}));
        $("[data-cmd=next]",g).disabled=seen>=rows.length;
        $("small",g).textContent=seen>=rows.length?"已显示全桥":"已显示 "+seen+"/"+rows.length+" 项，当前："+rows[seen-1].label;
    }
    g.onclick=e=>{const cmd=e.target.dataset.cmd;if(!cmd)return;seen=cmd==="start"?1:cmd==="all"?rows.length:Math.min(rows.length,seen+1);draw()};
    draw();
}
function overview(){
    const labels=["压力","基准","改善"];
    out("widget-overview",wrap("overview-card","同日估值区间","元／股 · 冻结模型 · 含权收盘为虚线",
        plot("scenario-plot")+`<div class="map">${[[2,"采购与续购"],[3,"历史检验"],[5,"利润到现金"],[7,"经营到预测"],[8,"价值与现价"],[9,"反证与抽查"],[10,"最终投资建议"]].map(([i,t])=>`<a href="#chapter-${String(i).padStart(2,"0")}"><span>第 ${String(i).padStart(2,"0")} 章</span>${t} ↗</a>`).join("")}</div>`+
        detail("展开三情景数值",kv(["路径","每股价值","相对收盘"],D.prices.map((p,i)=>[labels[i],f(p)+" 元",signed(p-D.market)+" 元"]))+raw("模型 JSON","model.json"))));
    scenarioPlot("scenario-plot",labels);
}
function scenarioPlot(id,labels){
    const xf=v=>145+v/150*510;
    let m=`<line class="price" x1="${xf(D.market)}" x2="${xf(D.market)}" y1="32" y2="164"/><text class="chart-label" x="${xf(D.market)}" y="23" text-anchor="middle">${f(D.market)} 元</text>`;
    D.prices.forEach((p,i)=>{
        const y=60+i*42;
        m+=`<line class="grid" x1="145" x2="655" y1="${y}" y2="${y}"/><text class="axis" x="125" y="${y+5}" text-anchor="end">${labels[i]}</text><circle cx="${xf(p)}" cy="${y}" r="7" fill="${palette[i]}"/><text class="chart-label" x="${xf(p)+12}" y="${y+5}">${f(p)}</text>`;
    });
    const title=D.prices.map((price,i)=>labels[i]+" "+f(price)).join("、")+" 元与收盘 "+f(D.market)+" 元";
    out(id,svg(title,m,720,175));
}
function conclusion(){
    const labels=["压力","基准","改善"];
    out("widget-conclusion",wrap("conclusion-card","三条路径与 96.20 元含权收盘","2026-11-12 · 元／股 · 虚线为含权收盘",
        plot("conclusion-plot")+
        detail("展开三情景数值",kv(["路径","每股价值","相对收盘"],D.prices.map((price,i)=>[labels[i],f(price)+" 元",signed(price-D.market)+" 元"])))+
        links([["逐年预测","#widget-forecast"],["旧新价值桥","#valuation-bridge"],["价格等值线","#valuation-contour"],["销量原证据","#volume-evidence"],["现金试算与底表","#cash-proof"],["本地批注（可选第 10 章）","#notes"]])));
    scenarioPlot("conclusion-plot",labels);
}
function roles(){
    const people=[
        ["光源与光学","光源和光学厂商提供光与光路；采购可由 OEM 完成。光源功率、光学器件与控制方案需要匹配。"],
        ["柏楚","柏楚提供控制、工艺以及部分切割头组合，收部件或方案款。技术支持、安装和担保按合同归属。"],
        ["整机厂 OEM","整机厂采购部件并整合机床，交付终端，先处理整机安装与验收。其向柏楚的账期由采购合同决定。"],
        ["终端车间","终端用材料、工件和产线实测良率、切割节拍及停机，按整机合同验收并支付整机款。"],
    ];
    const steps=[
        ["采购","整机厂按机型配置选控制器和切割头，确定净价及付款条款。"],
        ["交付","柏楚交付控制、软件和适用硬件，整机厂联调并承担约定集成工作。"],
        ["验收","终端测试样件、良率与稳定性；柏楚与设备厂的验收触发条件以各自合同为准。"],
        ["回款","终端支付整机款，设备厂向柏楚付款。售后、返工与质保仍可能在之后发生。"],
    ];
    out("widget-roles",wrap("roles-card","同一台设备的交付和资金流","原创机制示意 · 先选角色，再推进交付",
        tabs("role-tabs",people.map(([r],i)=>[i,r]))+`<div id="role-note" class="role-note" aria-live="polite"></div><h4>从采购到到账</h4><div class="actions stepbar" id="flow-steps">${steps.map(([s],i)=>`<button type="button" data-step="${i}">${i+1} ${s}</button>`).join("")}</div><div class="role-note" id="flow-note" aria-live="polite"></div>`+
        tabs("renew-tabs",[["renew","复用与续购"],["replace","自研与替代"]])+`<div id="renew-note" class="role-note" aria-live="polite"></div>`+links([["原报告产业链","#figure-chain"],["柏楚机制证据","original/batch1-mechanisms.md"]])));
    const person=i=>out("role-note","<b>"+people[i][0]+"</b><p>"+people[i][1]+"</p>");
    clickTabs("role-tabs",person);person(0);
    const step=i=>{
        $$("#flow-steps button").forEach((b,j)=>{b.classList.toggle("visited",j<=i);j===i?b.setAttribute("aria-current","step"):b.removeAttribute("aria-current");});
        out("flow-note","<b>"+steps[i][0]+"</b><p>"+steps[i][1]+"</p>");
    };
    $("#flow-steps").addEventListener("click",e=>{const b=e.target.closest("[data-step]");if(b)step(Number(b.dataset.step))});step(0);
    const renewal=k=>out("renew-note",k==="renew"?"工艺库和适配 → 调机与培训缩短 → 一次验收率改善 → 同型号复用。核同机型、同工件、同功率的工时、净价和连续采购。":"OEM 自研、多供应商及开放协议降低切换难度；行业换机与折扣同样可能增加销量。核分供应商净价、首次与替换台数、次期回款。");
    clickTabs("renew-tabs",renewal);renewal("renew");
}
function history(){
    const rows=D.history;
    const metrics={revenue:"营业收入",core_ebit:"核心 EBIT",cfo_less_capex:"CFO−购建",cfo:"经营现金流"};
    const notes={
        2019:"控制系统扩张与上市。2018 年比较列可回接招股书，采购规模变化仍要对应当时口径。",
        2020:"收入放量同时现金购建回落，现金改善受支出时点影响。",
        2021:"扩张延续，现金购建增加。与 2022 年构成利润与现金方向不同的对照。",
        2022:"收入回撤，核心利润承压。CFO 上升且现金购建减少，CFO−购建改善。",
        2023:"增长恢复。次年对保证类质量保证费用作比较重列，不能跨口径直接比毛利。",
        2024:"产品披露切换到应用解决方案，成本比较列及质保重列要按原报告回查。",
        2025:"智能硬件销售量快于控制系统。收入与组合上行，硬件的配套和单卖仍缺同设备分拆。",
        2026:"第三季单季收入增约 16.51%，核心 EBIT 增约 3.34%，毛利率下降约 5.76 个百分点。累计实绩独立展示。"
    };
    out("widget-history",wrap("history-card","经营时间轴","2019—2025 财年 · 百万元人民币 · 2026 年累计另列",
        tabs("history-metrics",Object.entries(metrics))+plot("history-plot")+
        `<div class="actions"><label for="history-year">查看年份</label><select id="history-year">${[...rows.map(x=>x.year),2026].map(y=>`<option value="${y}" ${y===2022?"selected":""}>${y===2026?"2026 前三季":y}</option>`).join("")}</select></div><div class="highlight" id="history-selected" aria-live="polite"></div>`+
        detail("上市前实绩 · 核对招股书",kv(["期间","原表科目","人民币元","物理 PDF 页"],D.preIpo.filter(x=>["营业总收入","营业利润","经营活动产生的现金流量净额"].includes(x["原行"])).map(x=>[x["期间"],x["原行"],f(x["原披露值"]),link("p"+x["PDF物理页"],x.URL+"#page="+x["PDF物理页"])]))+links([["招股书抽取及勾稽",source("pre-ipo.csv")]]))+
        detail("展开历史底表与原件",kv(["财年","营收","核心 EBIT","CFO","购建","CFO−购建"],rows.map(x=>[x.year,...["revenue","core_ebit","cfo","capex","cfo_less_capex"].map(k=>f(x[k]))]))+links([["财务底表 CSV",source("financial-bridge.csv")],["七份年报及季度定位",source("annual-evidence.csv")],["原报告历史图","#figure-history"]]))));
    let metric="revenue";
    const sel=()=>{
        const year=Number($("#history-year").value), row=rows.find(x=>x.year===year), prior=rows.find(x=>x.year===year-1);
        const idx=D.annual.find(x=>x.period===(year===2026?"2026-YTD9":year+"-FY"));
        const evidence=links([["披露原件·利润表 p"+idx.revenue_page,idx.url+"#page="+idx.revenue_page],["披露原件·现金流 p"+idx.cash_page,idx.url+"#page="+idx.cash_page]]);
        const show=row?`<b>${year} · ${metrics[metric]} ${f(row[metric])}</b>${prior?"（上年 "+f(prior[metric])+"）":""}`:
            `<b>2026 前三季实绩</b> · 营收 ${f(D.recent.revenue)}，核心 EBIT ${f(D.recent.core_ebit)} 百万元`;
        out("history-selected",show+`<p>${notes[year]}</p>`+evidence);
        out("history-plot",trend("历年"+metrics[metric],"百万元人民币",rows.map(x=>x.year),[{name:metrics[metric],color:palette[0],points:rows.map(x=>x[metric])}],{selected:rows.findIndex(x=>x.year===year),breakAt:5}));
    };
    clickTabs("history-metrics",k=>{metric=k;sel()});$("#history-year").addEventListener("change",sel);sel();
}
function volumeEvidence(){
    const ratios=D.volume.map(x=>pct(x.hardware_to_control_shipments));
    const single=Number(D.volume[1].hardware_units)-D.attach*Number(D.volume[1].control_units);
    return wrap("volume-reading","87.34% 的分母是什么","销售量列在生产量和库存量之间 · 套",
        `<div class="metrics">${card("2024 集团销量比",ratios[0],"硬件 ÷ 控制") }${card("2025 集团销量比",ratios[1],"AgentCalculated") }${card("2025 模型起点",pct(D.attach,0),"按设备配套的假设") }${card("倒算单卖当量",f(single)+" 套","情景派生")}</div>`+
        detail("核对 87.34% 年报原列",kv(["报告期","控制系统销售量","智能硬件销售量","硬件÷控制","原件"],D.cashSources.map((x,i)=>[x.year,x.lines.control.sales_raw,x.lines.hardware.sales_raw,ratios[i],link("物理第 "+x.physical_page+" 页",x.url+"#page="+x.physical_page)]))+
              caption("集团销量为实施 Agent 对读的原披露，两年资料的来源 ID 与 SHA-256 见复算回执。")+
              links([["55% 参数",gh("assumptions.json#L14")],["倒算公式",gh("forecast.py#L147-L150")],["销量年表",source("volume-and-stock.csv")],["11 月 24 日回执","audit/负现金复算回执.json"]]),"volume-evidence"));
}
function income(){
    out("widget-income",volumeEvidence()+wrap("income-card","收入和毛利的桥","采用值与比较重列 · 同一期间的主营口径",
        tabs("income-tabs",[["revenue","量价桥"],["gross","毛利瀑布"],["groups","产品／方案与重列"],["quarter","2026Q3 复核"]])+`<div id="income-step"></div>`+plot("income-plot")+
        `<div id="income-table"></div>`+links([["量价输入",source("volume-and-stock.csv")],["毛利贡献",source("gross-contribution.csv")],["重列区间",source("group-restatement.csv")],["成本性质",source("cost-attribution.csv")]])));
    const view=key=>{
        const chart=$("#income-plot").parentElement;
        chart.hidden=key==="groups"||key==="quarter";
        $("#income-step").hidden=chart.hidden;
        if(key==="revenue"){
            let cursor=0;
            const rows=D.revenueBridge.map((x,i)=>{
                const total=i===0||i===3;
                const result={label:x.item,short:["2024","量当量","组价组合","2025"][i],value:x.value,start:total?0:cursor,end:total?x.value:cursor+x.value,total};
                cursor=result.end;return result;
            });
            stepPlot("income-plot","income-step","2024→2025 主营收入量价桥",rows,"百万元人民币");
            out("income-table",kv(["项目","增量／合计（百万元）"],D.revenueBridge.map(x=>[x.item,f(x.value)]))+caption("按上年组均金额先分配出货量贡献，交互留在组均价和组合。数值为显示精度，未舍入净残差为零。"));
        }else if(key==="gross"){
            const set=D.gross.filter(x=>x.period==="24→25");
            const mix=set.reduce((sum,x)=>sum+Number(x.margin_mix_pp),0);
            const inside=set.reduce((sum,x)=>sum+Number(x.margin_inside_pp),0);
            const r=Math.min(0,mix+inside);
            stepPlot("income-plot","income-step","2024→2025 主营毛利率变动",[
                {label:"组合",value:mix,start:0,end:mix},
                {label:"组内",value:inside,start:mix,end:mix+inside},
                {label:"净变动",value:mix+inside,start:0,end:mix+inside,total:true}
            ],"百分点",{low:r-.6,high:1,ticks:1});
            out("income-table",kv(["方案","毛利增量（百万元）","组合（百分点）","组内（百分点）"],set.map(x=>[x.group,f(x.gross_delta_m),signed(Number(x.margin_mix_pp)),signed(Number(x.margin_inside_pp))]))+caption("中点分解均摊交互。毛利金额增加与毛利率下滑可同时发生。"));
        }else if(key==="groups"){
            out("income-table",caption("板卡、随动和总线属历史产品层；平面、管材、三维属应用层，可组合多类部件。2023 比较组收入使用披露增速相容区间，2024 原列与下年比较列分开。")+
                kv(["应用","2023 采用收入（百万元）","2024 收入","2025 收入"],D.restatement.map(x=>[x.group,f(Number(x.revenue23_adopted)/1e6),f(Number(x.revenue24)/1e6),f(Number(x.revenue25)/1e6)]))+
                kv(["成本类别","2024 原列（元）","2024 比较列（元）","差额（元）"],D.cost.map(x=>[x.name,f(x.year24_original),f(x.year24_comparison),signed(Number(x.delta_reclassification))]))+
                links([["2023 原产品表",source("2023-product-original.csv")],["原报告重列索引","original/report.md"]]));
        }else{
            const rows=["revenue","core_ebit","gross","cfo_less_capex","扣非归母"];
            const names=["营收","核心 EBIT","毛利","CFO−购建","扣非归母"];
            const vals=rows.map(x=>D.recentBridge.find(y=>y.item===x));
            const nm=v=>f(Number(v)/1e6);
            out("income-table",kv(["指标","2025Q3（百万元）","2026Q3（百万元）","同比"],vals.map((x,i)=>[names[i],nm(x.q3_25),nm(x.q3_26),pct(Number(x.q3_26)/Number(x.q3_25)-1)]))+
                caption("单季来自各期累计报表差分。毛利率同比下降约 5.76 个百分点。")+raw("完整季度桥","recent-income-bridge.csv"));
        }
    };
    clickTabs("income-tabs",view);view("revenue");
}

function cash(){
    const controls=[
        ["stock","库存天数",30,220,1,110," 天"],
        ["ar","应收天数",5,125,1,45," 天"],
        ["service","售后／每百元收入",0,20,.25,5," 元"],
        ["gm","硬件毛利率",30,70,1,50,"%"]
    ];
    const [base,slow]=D.cash;
    const input=base.all_inputs;
    const revenue=Number(input.net_sales), payDays=Number(input.ap_days), build=Number(input.gross_capex);
    const install=Number(input.installation), allowance=Number(input.control_allowance), tax=Number(input.cash_tax);
    const fixed=[["安装",install+" 元"],["控制折让",allowance+" 元"],["现金税率",pct(tax,0)],["应付",payDays+" 天"],["首批购建",build+" 元"]];
    out("widget-cash",wrap("cash-card","图表 23 · 配套首批现金","元／每 100 元增量硬件净收入 · 条件试算",
        `<div class="actions"><button type="button" id="preset-fast">库存 110／应收 45</button><button type="button" id="preset-slow">库存 150／应收 65</button></div>
        <div class="sliders">${controls.map(([k,name,min,max,step,value])=>`<label for="cash-${k}">${name}<output id="cash-${k}-value" for="cash-${k}"></output><input id="cash-${k}" type="range" min="${min}" max="${max}" step="${step}" value="${value}"></label>`).join("")}</div>
        <div id="cash-summary" class="metrics" aria-live="polite"></div>
        <p id="cash-reading" class="highlight" aria-live="polite"></p>`+plot("cash-plot")+
        detail("核对 −0.58 元的原输入、公式与回执",
          `<p class="formula">成本＝100 × (1−毛利率)<br>税后经营贡献＝(100−成本−安装−控制折让−售后) × (1−现金税率)<br>贸易占款＝(成本 × 库存天数＋100 × 应收天数−成本 × 应付天数) ÷ 365<br>首批现金＝税后经营贡献−贸易占款−现金购建</p>`+
          kv(["固定项","输入"],fixed)+kv(["库存／应收","首批现金（未舍入）","应收零点（天）"],D.cash.map(x=>[x.inventory_days+"／"+x.ar_days,x.cash,x.ar_days_zero]))+
          links([["冻结公式",gh("evidence.py#L171-L184")],["两格冻结 CSV",source("bundle-cash-thresholds.csv")],["复算回执","audit/负现金复算回执.json"],["原审阅图件","#figure-bundle"],["公司价格反推","#chapter-08"]]),"cash-proof")));
    const calculate=(stock,ar,service,gm)=>{
        const cost=revenue*(1-gm/100);
        const operating=(revenue-cost-install-allowance-service)*(1-tax);
        const inventory=cost*stock/365,receivable=revenue*ar/365,payable=cost*payDays/365;
        const capital=inventory+receivable-payable;
        return {cost,operating,inventory,receivable,payable,capital,cash:operating-capital-build,zero:((operating-build)*365-cost*(stock-payDays))/revenue};
    };
    const standard=calculate(base.inventory_days,base.ar_days,Number(base.all_inputs.service_scenario),Number(base.all_inputs.gross_margin)*100);
    function refresh(){
        const values=controls.map(([k,,,,,suffix])=>{
            const v=Number($("#cash-"+k).value);
            const readout=f(v,k==="service"&&v%1?2:0)+suffix;
            out("cash-"+k+"-value",readout);
            $("#cash-"+k).setAttribute("aria-valuetext",readout);
            return v;
        });
        const r=calculate(...values);
        const usable=r.operating-build;
        out("cash-summary",
            card("税后经营贡献",f(r.operating)+" 元")+" "+card("贸易占款",f(r.capital)+" 元")+" "+card("首批购建",f(build)+" 元")+
            `<div class="metric"><small>首批剩余现金</small><strong id="cash-result" class="${r.cash<0?"negative":"positive"}">${signed(r.cash)} 元</strong><small>现金零点：应收 ${f(r.zero,4)} 天</small></div>`);
        const shift=(label,v)=>label+"较 110／45 天预设"+(Math.abs(v)<1e-9?"持平":(v>0?"多占 ":"少占 ")+f(Math.abs(v))+" 元");
        const balance=Math.abs(r.cash)<1e-8?"可用资金刚好覆盖占款。":r.cash<0?`占款高于可用的 ${f(usable)} 元，首批需垫付 ${f(-r.cash)} 元。`:`占款低于可用的 ${f(usable)} 元，首批留下 ${f(r.cash)} 元。`;
        out("cash-reading",shift("库存",r.inventory-standard.inventory)+"，"+shift("应收",r.receivable-standard.receivable)+"，"+(Math.abs(r.payable-standard.payable)<1e-9?"应付抵扣持平。":`应付抵扣变化 ${signed(r.payable-standard.payable)} 元。`)+balance);
        const cashRows=[
            {label:"税后经营",value:r.operating,start:0,end:r.operating,total:true},
            {label:"贸易占款",value:-r.capital,start:r.operating,end:r.operating-r.capital},
            {label:"购建",value:-build,start:r.operating-r.capital,end:r.cash},
            {label:"首批现金",value:r.cash,start:0,end:r.cash,total:true}
        ];
        out("cash-plot",waterfall("首批配套现金桥",cashRows,"元／每百元收入",{low:Math.min(-3,r.cash*1.2)}));
    }
    controls.forEach(([k])=>$("#cash-"+k).addEventListener("input",refresh));
    const preset=(row)=>{
        const values=[row.inventory_days,row.ar_days,Number(row.all_inputs.service_scenario),Number(row.all_inputs.gross_margin)*100];
        controls.forEach(([k],i)=>{$("#cash-"+k).value=values[i]});
        refresh();
    };
    $("#preset-fast").onclick=()=>preset(base);
    $("#preset-slow").onclick=()=>preset(slow);
    preset(base);
}
function projects(){
    const stages=["可服务需求","适配","订单","验收","回款","资本回报"];
    out("widget-projects",wrap("project-card","商业化阶段矩阵","点项目切换证据 · 期后说明会单独记载",
        tabs("project-tabs",D.projects.map((p,i)=>[i,p.project]))+`<div id="project-data" aria-live="polite"></div>`+
        detail("展开全部项目阶段及募投原件",
            kv(["项目",...stages],D.projects.map(p=>[p.project,...stages.map(k=>enc(p[k]))]))+
            links([["阶段矩阵 CSV",source("commercialization-stages.csv")],["募投原表定位",source("project-stages.csv")],["项目条件规模",source("project-conditional-scale.csv")],["期后及权益事件",source("post-window.csv")]]))));
    const change=i=>{
        const row=D.projects[i];
        const p=D.projectStages[0];
        const annual=D.annual.find(x=>x.period==="2025-FY");
        const projectLink=link("募投结项公告 p"+p["PDF物理页"],p.URL+"#page="+p["PDF物理页"]);
        out("project-data",`<div class="stages">${stages.map(k=>`<div class="stage"><small>${k}</small><b>${enc(row[k])}</b></div>`).join("")}</div>
          <p class="highlight"><b>最高已证阶段 · ${enc(row.highest_stage)}</b><br>入模条件 · ${enc(row.model_gate)}</p>
          <p class="meta">${enc(row.original_evidence)}。${enc(row.locator)}。</p>
          <div class="linkrow">${projectLink} · ${link("2025 年报",annual.url)} · ${link("11 月 20 日路演（期后）","https://roadshow.sseinfo.com/activityDetails/42275")}</div>`);
    };
    clickTabs("project-tabs",change);change(0);
}
function forecast(){
    const choices=[["base","基准"],["stress","压力"],["improve","改善"]];
    const metrics={control_units:["控制量","套"],revenue:["营收","百万元"],core_ebit:["核心 EBIT","百万元"],fcff:["FCFF","百万元"]};
    const flow=[
        ["设备需求","新机＝可服务设备×适配比例×订单份额。存量换机采用历史装机当量和轮换周期。"],
        ["控制订单","已经分到新机的设备只计一次；存量端继续乘同机型续购条件。"],
        ["配套与验收","配套从 55% 模型起点按情景递推，独卖分开，延期验收影响当期匹配确认。"],
        ["收入与利润","已验收的数量乘净价。成本、费用及售后由情景一起计算，得到核心 EBIT。"],
        ["FCFF","税后经营利润加折旧，再扣增量经营占款及现金购建。估值日后桩段单独折现。"]
    ];
    const colors={base:"#1f765d",stress:"#bd684d",improve:"#856497"};
    const dash={base:"",stress:"6 5",improve:"12 5 3 5"};
    out("widget-forecast",wrap("forecast-card","由设备到自由现金流","2026 全年估计接入已披露前三季 · 2027—2035 为模型预测",
        tabs("driver-tabs",flow.map(([s],i)=>[i,s]))+`<p class="role-note" id="driver-text" aria-live="polite"></p>`+
        tabs("forecast-scenarios",choices)+tabs("forecast-metrics",Object.entries(metrics).map(([k,[label]])=>[k,label]))+
        plot("forecast-plot")+`<div class="legend" id="forecast-legend"></div><div id="forecast-note" aria-live="polite"></div>`+
        detail("展开逐年模型与实绩桥",`<div id="forecast-data"></div>`+links([["逐年 CSV",source("forecast.csv")],["2026Q3 单季与累计",source("recent-income-bridge.csv")],["历史留出",source("annual-holdouts.csv")],["券商复算",source("analyst-unit-test.csv")],["逐年预测程序",gh("forecast.py")]]))));
    const showDriver=i=>out("driver-text",flow[i][1]);clickTabs("driver-tabs",showDriver);showDriver(0);
    let scenario="base",field="control_units";
    function render(){
        const rows=D.forecast.filter(x=>x.scenario===scenario);
        const [name,unit]=metrics[field];
        const projected=rows.map(x=>Number(x[field]));
        const legend=`<span><i class="swatch" style="background:${colors[scenario]}"></i>${choices.find(x=>x[0]===scenario)[1]}路径</span><span>2026E 含前三季实绩</span>`+
          (field==="fcff"?`<span><i class="dashed swatch"></i>估值日后桩段见下表</span>`:"");
        out("forecast-plot",trend("逐年"+name,unit,rows.map(x=>x.year==="2026"?"2026E":x.year),[{name,color:colors[scenario],dash:dash[scenario],points:projected}],{selected:0,breakAt:1,breakLabel:"完整预测期"}));
        out("forecast-legend",legend);
        out("forecast-note",`<p class="highlight"><b>${choices.find(x=>x[0]===scenario)[1]} · 2027 ${name} ${f(projected[1])} ${unit}</b><br>2026 前三季实绩：营业收入 ${f(D.recent.revenue)} 百万元、核心 EBIT ${f(D.recent.core_ebit)} 百万元。估值日后桩段 FCFF ${f(rows[0].valued_cash)} 百万元；2026 全年估计 FCFF ${f(rows[0].fcff)} 百万元。</p>`);
        out("forecast-data",kv(["财年","控制量（套）","收入（百万元）","核心 EBIT","FCFF","估值用现金"],rows.map(x=>[x.year==="2026"?"2026E（全年）":x.year,f(x.control_units,0),f(x.revenue),f(x.core_ebit),f(x.fcff),f(x.valued_cash)]))+caption("2026 年「估值用现金」为日后桩段。未披露控制实绩与合并 FCFF 时，预测文件留相应识别边界。"));
    }
    clickTabs("forecast-scenarios",k=>{scenario=k;render()});
    clickTabs("forecast-metrics",k=>{field=k;render()});render();
}
function valuation(){
    const choices=[["waterfall","旧新价值桥"],["contour","96.20 元等值线"],["equity","企业到普通股"]];
    const groups=[
        ["tight","库存 +25 天 · 售后 +2pp",25,"#ab5e45","7 5"],
        ["base","周转及售后维持基准",0,"#246f59",""],
        ["light","库存 −25 天 · 售后 −0.6pp",-25,"#785d94","13 5 2 5"]
    ];
    const xs=[...new Set(D.nodes.map(x=>x.computed_2027_volume_growth))];
    const marginRange=D.nodes[0];
    const c=D.cases.base;
    out("widget-valuation",wrap("valuation-card","价格要求的联合条件","同步比较冻结旧值、新值和当天含权价格",
        `<div class="metrics">${card("旧基准",f(D.bridge[0].price_after)+" 元") }${card("新基准",f(c.price)+" 元") }${card("含权收盘",f(D.market)+" 元") }${card("终值占 EV",pct(c.terminal_share)) }</div>`+
        kv(["压力","基准","改善"],[D.prices.map(x=>f(x)+" 元／股")])+tabs("valuation-tabs",choices)+`<div id="valuation-visual"><div id="valuation-step"></div>${plot("valuation-plot")}</div><div id="valuation-context"></div>`+
        links([["价值桥 CSV",source("value-bridge.csv")],["价格等值节点",source("price-contours.csv")],["权益桥",source("equity-bridge.csv")],["独立复算底稿",source("independent-audit.json")]])));
    function bridge(){
        const names=["旧值","桩段","NOPAT","再投资","终值","WACC","权益"];
        const steps=D.bridge.map((x,i)=>({label:x.item,short:names[i],start:i?Number(D.bridge[i-1].price_after):78,end:Number(x.price_after),value:Number(i?x.share_delta:x.price_after),total:!i}));
        steps.push({label:"新值",short:"新值",start:78,end:c.price,value:c.price,total:true});
        $("#valuation-step").hidden=false;
        stepPlot("valuation-plot","valuation-step","冻结价值到本稿基准价值",steps,"元／股 · 截断纵轴",{low:78,high:95});
        out("valuation-context",detail("展开未舍入的价值桥",kv(["因素","每股差额（元）","变化后价值（元）"],D.bridge.map(x=>[x.item,x.item==="冻结基准"?"—":x.share_delta,x.price_after]))));
    }
    function contour(){
        $("#valuation-step").hidden=true;
        out("valuation-plot",trend("96.20 元价格等值线","稳定核心 EBIT 利润率（%）",xs.map(x=>f(Number(x)*100,2)),groups.map(([,name,shift,color,dash])=>({
            name, color,dash,points:xs.map(v=>{const row=D.nodes.find(x=>Number(x.inventory_days_shift)===shift&&x.computed_2027_volume_growth===v);return row.root===""?null:Number(row.stable_core_ebit_margin)*100;})
        })),{lo:53,hi:62,digits:1,hatch:true,xLabel:"2027 控制量增速（%）"}));
        out("valuation-context",`<div class="legend">${groups.map(([,name,,color,dash])=>`<span><i class="swatch ${dash?"dashed":""}" style="background:${dash?"transparent":color};border-color:${color}"></i>${name}</span>`).join("")}<span><i class="swatch hatch"></i>低量节点无根</span></div>
        <p class="meta">只连接已验根。斜纹对应已列 1.71% 与 3.71% 节点。求根时稳定核心 EBIT 利润率的模型调整项固定在 ${pct(marginRange.lower,0)} 到 ${pct(marginRange.upper,0)} 的搜索区间，其他经营、估值参数沿原底表固定。线段用于对比离散节点。</p>
        <div class="actions"><label for="price-node">核对 2027 控制量增速节点</label><select id="price-node">${xs.map((x,i)=>`<option value="${x}" ${i===5?"selected":""}>${pct(x)}</option>`).join("")}</select></div><div id="price-node-readout" aria-live="polite"></div>`);
        const readNode=()=>{
            const chosen=$("#price-node").value;
            const rows=groups.map(([,name,shift])=>{
                const a=D.nodes.find(x=>x.computed_2027_volume_growth===chosen&&Number(x.inventory_days_shift)===shift);
                return a.root!==""?[name,pct(a.stable_core_ebit_margin),f(a.reprice)+" 元；残差 "+Number(a.residual).toExponential(2)]:[name,"原区间无解",f(a.lower_price)+"～"+f(a.upper_price)+" 元；上界距收盘 "+f(D.market-Number(a.upper_price))+" 元"];
            });
            out("price-node-readout",kv(["库存与售后","稳定利润率","回代或边界"],rows));
        };
        $("#price-node").addEventListener("change",readNode);readNode();
    }
    function equity(){
        out("valuation-context",`<div class="metrics">${card("显性期现值",f(c.explicit_pv),"百万元") }${card("终值现值",f(c.terminal_pv),"百万元") }${card("企业价值",f(c.enterprise_value),"百万元") }${card("股东权益价值",f(c.equity_value),"百万元") }</div>`+
            caption("基准 WACC "+pct(c.wacc)+"，长期增长 "+pct(c.growth)+"，新增 ROIC "+pct(c.roic)+"，稳定期再投资率 "+pct(c.growth/c.roic)+"。估值日股数 405,984,426。")+
            kv(["账户","计入权益（百万元）","每股影响（元）","定位"],D.equity.map(x=>[enc(x.item),f(x.delta_m),signed(Number(x.delta_per_share)),enc(x.locator)])));
    }
    const go=k=>{
        $("#valuation-visual").hidden=k==="equity";
        if(k==="waterfall")bridge();else if(k==="contour")contour();else equity();
    };
    clickTabs("valuation-tabs",go);
    $('#valuation-tabs [data-key="waterfall"]').id="valuation-bridge";
    $('#valuation-tabs [data-key="contour"]').id="valuation-contour";
    bridge();
}
function notes(){
    const noteKey="bochu-atlas-v1";
    let store={}, storage;
    try{storage=window.localStorage;store=JSON.parse(storage.getItem(noteKey)||"{}")||{};}catch{storage=null;}
    const section=$("#notes-chapter"),input=$("#note-text"),output=$("#note-status");
    function place(){input.value=store[section.value]||"";output.textContent="正在编辑第 "+section.value+" 章批注";}
    section.onchange=place;
    $("#note-save").onclick=()=>{
        store[section.value]=input.value;
        try{
            if(!storage)throw Error();
            storage.setItem(noteKey,JSON.stringify(store));
            output.textContent="已保存在本浏览器。";
        } catch{output.textContent="本浏览器限制文件存储，请导出批注。";}
    };
    $("#note-export").onclick=()=>{
        store[section.value]=input.value;
        const uri=URL.createObjectURL(new Blob([JSON.stringify({title:"柏楚电子图册批注",archive:D.meta.archive_commit,notes:store},null,2)],{type:"application/json;charset=utf-8"}));
        const a=document.createElement("a");a.href=uri;a.download="柏楚电子-本地批注.json";a.click();setTimeout(()=>URL.revokeObjectURL(uri),1000);
        output.textContent="已请求下载批注 JSON。";
    };
    place();
}
function review(){
    out("widget-review",wrap("review-card","把证据落实到需要修改的判断","原披露、算术、情景与采纳各有记录",
        detail("查配套判断的上修条件",`<p>按 OEM、机型、验收窗口及设备号取得控制和硬件匹配，留净价、返利退换、安装质保、应收、库存、应付及实收。正向样本还要持续产生扣完购建后的现金。</p>`+link("源证据卡","audit/抽查证据卡与拟改正文.md"),"thesis-proof")+
        detail("查配套判断的下修条件",`<p>同机型净价下滑、延迟验收、库龄上升、付款更慢和售后发生率恶化，会使单位现金变薄。对照品类周转和回款批次区分安全备货和滞销。</p>`+raw("库存与配置的量化入口","volume-and-stock.csv"))+
        `<h4>老师抽查路线</h4><ol><li>${link("87.34% 原表路线","#volume-evidence")} → 年报「销售量」列 → 55% 参数与倒算 → ${link("图表 23 公式与回执","#cash-proof")}。</li><li>${link("配套判断与采纳","#decision-record")} → ${link("11 月 24 日完整抽查记录","audit/老师抽查路线与改前改后.md")} → ${link("现金复算回执","audit/负现金复算回执.json")}。</li></ol>
        <div id="decision-record" class="highlight"><b>判断与复核身份</b><p>实施 Agent 对读年报并复算，看到集团相对销量上升，图册收窄表述并沿用冻结估值。原始输入重算得到负现金 −4211/7300 元。发行人 ReviewStore 回执记录 ${D.facts} 条当时有效 Fact，销量单元格无独立确认绑定。提词器独立抽核待登记。</p></div>
        <details class="notes" id="notes"><summary>本地批注</summary><label for="notes-chapter">批注章节</label><select id="notes-chapter">${D.title.map((x,i)=>`<option value="${String(i+1).padStart(2,"0")}" ${i===8?"selected":""}>${String(i+1).padStart(2,"0")} · ${enc(x)}</option>`).join("")}</select><label for="note-text">审阅记录</label><textarea id="note-text" placeholder="记录原件页、变量或需确认的事项"></textarea><div class="actions"><button id="note-save" type="button">保存批注</button><button id="note-export" type="button">导出 JSON</button></div><output id="note-status" aria-live="polite"></output></details>`));
    notes();
}

function setupUI(){
    const sections=$$(".chapter");
    const mobile=$("#nav-toggle"), nav=$("#nav-area");
    function toggleMenu(open){
        nav.classList.toggle("open",open);
        mobile.setAttribute("aria-expanded",String(open));
        $("span",mobile).textContent=open?"−":"＋";
    }
    mobile.onclick=()=>toggleMenu(!nav.classList.contains("open"));
    const first=$("#all-original");
    const reportDetails=$$(".chapter .original");
    first.onclick=()=>{
        const open=first.getAttribute("aria-pressed")!=="true";
        reportDetails.forEach(d=>{d.open=open});
        first.setAttribute("aria-pressed",String(open));
        first.textContent=open?"收起各章原文":"展开各章原文";
    };

    const search=$("#search-dialog"), dialog=$("#zoom-dialog");
    const input=$("#search-input"), list=$("#results");
    let origin=null;
    const open=(modal)=>{
        origin=document.activeElement;
        modal.showModal();
    };
    for(const modal of [search,dialog]){
        $("[data-close]",modal).onclick=()=>modal.close();
        modal.addEventListener("close",()=>{if(origin?.isConnected)origin.focus({preventScroll:true});});
    }
    $("#search-open").onclick=()=>{
        open(search);
        input.focus();
        if(input.value)input.select();
    };
    document.addEventListener("keydown",e=>{
        if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"&&!search.open&&!dialog.open){
            e.preventDefault();$("#search-open").click();
        }
        if(e.key==="Escape"&&!search.open&&!dialog.open&&nav.classList.contains("open"))toggleMenu(false);
    });
    document.addEventListener("click",e=>{
        const a=e.target.closest("a[href^='#']");
        if(a){
            const id=a.getAttribute("href");
            if(id.startsWith("#chapter-")||id==="#sources")toggleMenu(false);
            if(search.open)search.close();
            reveal(id);
        }
        const target=e.target.closest("[data-zoom]");
        if(target){
            const graphic=$("#"+target.dataset.zoom+" svg");
            if(!graphic)return;
            const picture=graphic.cloneNode(true);
            for(const node of $$("[id]",picture)){
                const original=node.id, changed="zoom-"+original;
                node.id=changed;
                for(const item of $$("[fill]",picture))if(item.getAttribute("fill")==="url(#"+original+")")item.setAttribute("fill","url(#"+changed+")");
            }
            $("#zoom-title").textContent=$("title",graphic).textContent;
            $("#zoom-content").replaceChildren(picture);
            $("#zoom-content").className="chart zoom-picture";
            open(dialog);
            return;
        }
        const img=e.target.closest(".archive-fig img");
        if(img){
            $("#zoom-title").textContent=img.alt||"归档图件";
            $("#zoom-content").replaceChildren(img.cloneNode());
            $("#zoom-content").className="zoom-picture";
            open(dialog);
        }
    });
    $$(".archive-fig img").forEach(img=>{
        img.tabIndex=0;
        img.setAttribute("role","button");
        img.setAttribute("aria-label","放大图件 "+img.alt);
        img.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();img.click();}});
    });
    function reveal(hash){
        if(!hash||hash==="#")return;
        const item=document.getElementById(decodeURIComponent(hash.slice(1)));
        if(!item)return;
        if(item.matches("#valuation-bridge,#valuation-contour")&&item.getAttribute("aria-pressed")!=="true")item.click();
        for(let node=item;node;node=node.parentElement)if(node.tagName==="DETAILS")node.open=true;
        item.classList.remove("flash");
        requestAnimationFrame(()=>item.classList.add("flash"));
    }
    window.addEventListener("hashchange",()=>{
        reveal(location.hash);
        const target=sections.find(section=>"#"+section.id===location.hash);
        if(target){
            target.scrollIntoView({behavior:"instant"});
            updateProgress(target.id);
        }
    });
    if(location.hash){
        reveal(location.hash);
        requestAnimationFrame(()=>document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView());
    }
    function lookup(){
        const q=input.value.trim().toLocaleLowerCase();
        if(!q){list.innerHTML="<p>可查正文、原报告或具体金额。</p>";return;}
        const preferred=[
            ["87.34% 销量与年报原列","volume-evidence","87.34% 57.58% 55% 21,038.80 销量"],
            ["图表 23 负现金公式","cash-proof","−0.58 -0.58 62.8945 库存 应收 现金"],
            ["归档的独立复算与裁定","decision-record","配套 裁定 提词器 证据"],
            ["96.20 元价格等值线","valuation-card","96.20 收盘 等值 无解 81.81"]
        ];
        const results=preferred.filter(([, ,text])=>text.toLocaleLowerCase().includes(q)).map(([label,id,text])=>[label,id,text]);
        for(const chapter of sections){
            const header=$("h2",chapter).textContent;
            const nodes=$$(".prose>p,.archive-body p",chapter);
            for(const paragraph of nodes){
                const message=paragraph.textContent;
                const at=message.toLocaleLowerCase().indexOf(q);
                if(at<0)continue;
                if(!paragraph.id)paragraph.id=chapter.id+"-p"+nodes.indexOf(paragraph);
                results.push([header,paragraph.id,message.slice(Math.max(0,at-25),at+70)]);
                break;
            }
        }
        list.innerHTML=results.length?results.map(([label,id,text])=>`<a href="#${id}">${enc(label)}<small>${enc(text)}</small></a>`).join(""):"<p>未找到该关键词。</p>";
    }
    input.addEventListener("input",lookup);lookup();

    function updateProgress(chapter){
        const range=document.documentElement.scrollHeight-window.innerHeight;
        const value=range>0?Math.max(0,Math.min(100,Math.round(scrollY/range*100))):100;
        $("#reading").value=value;
        $("#progress-label").textContent=value+"%";
        let current=typeof chapter==="string"?chapter:null;
        if(!current){
            const readingLine=Math.max(145,window.innerHeight/4);
            for(const section of sections)if(section.getBoundingClientRect().top<=readingLine)current=section.id;
        }
        for(const anchor of $$("#nav-area nav a")){
            if(anchor.getAttribute("href")==="#"+current)anchor.setAttribute("aria-current","location");
            else anchor.removeAttribute("aria-current");
        }
    }
    let scrollTick=0;
    window.addEventListener("scroll",()=>{if(scrollTick)return;scrollTick=requestAnimationFrame(()=>{scrollTick=0;updateProgress();});},{passive:true});
    window.addEventListener("resize",updateProgress);
    updateProgress();
}
overview();roles();history();income();cash();projects();forecast();valuation();review();conclusion();setupUI();
