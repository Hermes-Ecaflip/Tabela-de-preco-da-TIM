/* Simulador de comissionamento — regras transcritas da planilha fornecida */
(() => {
  const money = value => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value)||0);
  const num = id => Math.max(0, Number(document.getElementById(id)?.value)||0);
  const set = (id,value) => { const el=document.getElementById(id); if(el) el.textContent=value; };
  const services = [
    ['Up Grade Mesma Categoria',10],
    ['Pós Individual → Pós Família Titular',40],
    ['Controle → Pós Individual',40],
    ['Controle → Pós Família Titular',80],
    ['Portabilidade',20],
    ['Fibra Instalada (Fibra Alone)',50],
    ['Fibra Convergência',30],
    ['TIM PLAY Básico',10.77],
    ['TIM PLAY Essencial',16.77],
    ['TIM PLAY Plus',22.77],
    ['TIM PLAY Premium',26.97],
    ['TIM PLAY VIP',37.77]
  ];
  const films = [['Até R$ 49,99',3],['De R$ 50,00 a R$ 98,99',5],['De R$ 99,00 a R$ 128,99',10],['De R$ 129,00 a R$ 148,99',15],['Acima de R$ 149,00',20]];
  const obsolete = [['Abaixo de R$ 1.000,00',40],['Acima de R$ 1.000,00',60]];
  const row = (name,rate,index,prefix) => `<tr><td>${name}</td><td><input type="number" min="0" step="1" value="0" id="${prefix}Qty${index}" aria-label="Quantidade: ${name}"></td><td>${money(rate)}</td><td id="${prefix}Total${index}">${money(0)}</td></tr>`;
  document.getElementById('serviceCommissionRows').innerHTML=services.map(([n,r],i)=>row(n,r,i,'service')).join('');
  document.getElementById('filmCommissionRows').innerHTML=films.map(([n,r],i)=>row(n,r,i,'film')).join('');
  document.getElementById('obsoleteCommissionRows').innerHTML=obsolete.map(([n,r],i)=>row(n,r,i,'obsolete')).join('');
  const allInputs=[...document.querySelectorAll('#modeCommission input, #modeCommission select')];
  function calculate(){
    const serviceFixed=services.reduce((sum,[,rate],i)=>{const v=num(`serviceQty${i}`)*rate;set(`serviceTotal${i}`,money(v));return sum+v;},0);
    const revenueCommission=num('contractedRevenue')*Number(document.getElementById('serviceTier').value);
    const serviceTotal=serviceFixed+revenueCommission;
    set('serviceFixedSubtotal',money(serviceFixed));set('serviceRevenueCommission',money(revenueCommission));set('serviceGrandTotal',money(serviceTotal));

    const device=num('deviceRevenue'), obsRev=num('obsoleteRevenue'), chip=num('chipRevenue'), timAcc=num('timAccessoryRevenue');
    const revenueTotal=device+obsRev+chip+timAcc;
    let tier='Sem comissão', rate=0;
    if(revenueTotal>=15000&&revenueTotal<=25000){tier='Branca';rate=.0075;}
    else if(revenueTotal<=35000&&revenueTotal>25000){tier='Amarela';rate=.0125;}
    else if(revenueTotal<=50000&&revenueTotal>35000){tier='Azul';rate=.02;}
    else if(revenueTotal>50000){tier='Preta';rate=.03;}
    const deviceComm=device*rate, generalComm=num('generalAccessoryRevenue')*.06, insuranceComm=num('insuranceRevenue')*.06, timComm=revenueTotal>=15000?timAcc*.005:0;
    set('productRevenueTotal',money(revenueTotal));set('productTier',tier);set('deviceCommissionRate',`Comissão de aparelhos: ${(rate*100).toLocaleString('pt-BR')}%`);set('deviceRateText',`${(rate*100).toLocaleString('pt-BR')}%`);
    set('deviceCommission',money(deviceComm));set('generalAccessoryCommission',money(generalComm));set('insuranceCommission',money(insuranceComm));set('timAccessoryCommission',money(timComm));
    const filmTotal=films.reduce((sum,[,r],i)=>{const v=num(`filmQty${i}`)*r;set(`filmTotal${i}`,money(v));return sum+v;},0);
    const obsoleteTotal=obsolete.reduce((sum,[,r],i)=>{const v=num(`obsoleteQty${i}`)*r;set(`obsoleteTotal${i}`,money(v));return sum+v;},0);
    const productTotal=deviceComm+generalComm+insuranceComm+timComm+filmTotal+obsoleteTotal;
    set('filmCommissionTotal',money(filmTotal));set('obsoleteCommissionTotal',money(obsoleteTotal));
    set('commissionServicesTotal',money(serviceTotal));set('commissionProductsTotal',money(productTotal));set('commissionGrandTotal',money(serviceTotal+productTotal));
    set('finalServices',money(serviceTotal));set('finalProducts',money(productTotal));set('finalGrandTotal',money(serviceTotal+productTotal));
  }
  allInputs.forEach(el=>el.addEventListener('input',calculate));
  document.getElementById('commissionReset').addEventListener('click',()=>{
    allInputs.forEach(el=>{if(el.tagName==='SELECT')el.selectedIndex=0;else el.value='0';});
    calculate();
  });
  calculate();
})();