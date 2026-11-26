function calculate(M,name,wacc,g,margin=0,days=0,cap=1){
 const s=M.cases[name],B=M.base;let rev=[...B.revenue],prevNW=B.nwc,prevNOP=null,prevRev=B.totalRevenue,years=[];
 for(let i=0;i<10;i++){
  const fade=i/9;rev=rev.map((r,j)=>r*(1+s.g0[j]*(1-fade)+g*fade));
  const gm=B.gm.map((x,j)=>x+(s.gmEnd[j]-x)*Math.min((i+1)/5,1)+margin);
  const total=rev.reduce((a,b)=>a+b,0),cost=rev.reduce((a,r,j)=>a+r*(1-gm[j]),0);
  const ebit=total-cost-total*(s.sales+s.admin+s.rd+.013+.002),tax=Math.max(ebit,0)*s.tax,nop=ebit-tax;
  const nw=total*(s.days+days)/365+cost*s.inv/365+cost*B.prepayRate-cost*s.ap/365-total*(s.disc+s.dep),dn=nw-prevNW;
  const da=total*B.da/B.totalRevenue,expansion=Math.max(total-prevRev,0)/s.sc;let capex=(da+expansion)*cap;
  const mix=Math.max(0,(i-6)/3);
  if(prevNOP!==null)capex=capex*(1-mix)+(da+Math.max(nop-prevNOP,0)/s.roic-dn)*mix;
  const fcff=nop+da-capex-dn;
  years.push({year:2026+i,revenue:total,core_ebit:ebit,nopat:nop,da,delta_nwc:dn,capex,fcff,pv:fcff/(1+wacc)**(i+1)});
  prevNW=nw;prevNOP=nop;prevRev=total;
 }
 const terminalNOP=years.at(-1).nopat*(1+g),terminalFCFF=terminalNOP*(1-g/s.roic),
 terminalPV=terminalFCFF/(wacc-g)/(1+wacc)**10,explicit=years.reduce((a,r)=>a+r.pv,0),
 bridge=B.cash-B.cashReserve+B.financial-B.debt-B.minority,ev=explicit+terminalPV;
 return {price:(ev+bridge)/B.shares,explicit_pv:explicit,terminal_pv:terminalPV,ev,bridge,years};
}
if(typeof module!=='undefined')module.exports={calculate};
