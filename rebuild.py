from pathlib import Path
import json

p_in = Path('/data/.openclaw/media/inbound/Ciudad_del_Valle_Formalizacion_marzo2026---01bf6ada-2ffe-404d-a7cc-db3328c53ddc')
html = p_in.read_text()

# --- 1) NAV: add vendedor tab
html = html.replace('<div class="nav-tab" data-view="formalizador" onclick="switchView(\'formalizador\')">👤 Por Formalizador</div>',
                    '<div class="nav-tab" data-view="formalizador" onclick="switchView(\'formalizador\')">👤 Por Formalizador</div>\n    <div class="nav-tab" data-view="vendedor" onclick="switchView(\'vendedor\')">🤝 Por Vendedor</div>')

# --- 2) FILTERS: add vendedor and status selects
marker = '<span class="filter-label">Filtros:</span>'
filter_vendedor = '<select class="filter-select" id="filterVendedor" onchange="applyFilters()"><option value="">Todos los vendedores</option></select>'
filter_estado = '<select class="filter-select" id="filterEstado" onchange="applyFilters()"><option value="">Todos los estados</option><option value="Sin reunion de inicio">Sin reunion de inicio</option><option value="Reunion de inicio">Reunion de inicio</option><option value="Casa iniciada">Casa iniciada</option><option value="Terminada">Terminada</option></select>'
html = html.replace(marker, f"{marker}\n    {filter_vendedor}\n    {filter_estado}")

# --- 3) VIEW panels
html = html.replace('<div id="viewFormalizador" class="view-panel"></div>',
                    '<div id="viewFormalizador" class="view-panel"></div>\n  <div id="viewVendedor" class="view-panel"></div>')

# --- 4) TABLE HEADERS
html = html.replace('<th>Banco</th>\n              <th>Formalizador</th>',
                    '<th>Banco</th>\n              <th>Vendedor</th>\n              <th>Estado</th>\n              <th>Formalizador</th>')

# --- 5) TABLE ROWS
row_bank = '<td data-label="Banco"><span class="bank-tag">${c.banco}</span></td>'
html = html.replace(row_bank, row_bank + '\n      <td data-label="Vendedor"><span class="bank-tag" style="background:#E5E7EB;color:#374151">${c.vendedor||\'\'}</span></td>\n      <td data-label="Estado">${renderEstadoSelect(c)}</td>')

# --- 6) DATE CELL
html = html.replace('<td data-label="Fecha Est.">${formatDate(c.fecha)}</td>',
                    '<td data-label="Fecha Est."><input type="date" class="fecha-input" data-lote="${c.lote}" value="${c.fecha}" style="padding:6px 10px;border:1px solid var(--border);border-radius:8px;font-family:inherit;font-size:12px"></td>')

# --- 7) CASAS Dataset
casas = [
  dict(lote="M.23", modelo="Stella A 2D 2.5B WC L(PA)", modeloBase="Stella", cliente="Hernan Nuñez Fioravantti", montoCasa=17000000, loteAD=10026955, loteQFI=7183827, fecha="2026-03-23", banco="BCR", formalizador="Hazel", vendedor="Olman", traspaso=True, permisos=True, capacidad="✅", pendientes="avalúo solicitado, en proceso pago de bono vivienda, para proceder con la venta de la casa y con esto el cliente tenga capacidad", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="K.14", modelo="Neo Tripoli A 3D 2B WC OF", modeloBase="Neo Tripoli", cliente="Jean Monge Bonilla", montoCasa=14000000, loteAD=8926156, loteQFI=7844306.4, fecha="2026-03-16", banco="Coopeande", formalizador="Hazel", vendedor="Irving", traspaso=True, permisos=True, capacidad="Cliente con capacidad para ¢80.0MM, la diferencia hay que financiarla, cliente ya tiene préstamo por ¢6.0MM", pendientes="avalúo solicitado, a la espera de que Victor confirme que paso la revisión legal.", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="D.21", modelo="Ikaria A 2D 2B WC", modeloBase="Ikaria", cliente="Mauricio Valverde Céspedes", montoCasa=73800000, loteAD=10605988, loteQFI=6836407.2, fecha="2026-03-23", banco="BN", formalizador="Hazel", vendedor="Hannia", traspaso=True, permisos=True, capacidad="A espera de que cancele deuda para tener capacidad de pago", pendientes="Documentación actualizada", terminada=True, estadoCasa="Terminada"),
  dict(lote="L.53", modelo="Zante T 4D 2.5B WC (PA)", modeloBase="Zante", cliente="Karen Vizcaino Vargas", montoCasa=22000000, loteAD=9226277.5, loteQFI=7664233.5, fecha="2026-03-28", banco="Coopenae", formalizador="Hazel", vendedor="Randall", traspaso=True, permisos=True, capacidad="Cliente hoy paso parte de la información, se esta revisando.", pendientes="revisandose información, cliente independiente no factura y declara en cero, se vio el caso con Coopenae. Caso un poco complicado ya que los estados no reflejan los ingresos.", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="M.07", modelo="Santorini T 3D 2.5B WC OF F30", modeloBase="Santorini", cliente="Andres Ureña Abarca", montoCasa=24000000, loteAD=8563362, loteQFI=9261982.8, fecha="2026-03-23", banco="Mucap", formalizador="Hazel", vendedor="Xinia", traspaso=True, permisos=True, capacidad="A espera de información del cliente", pendientes="Caso con Mucap, cliente con estados de cuenta pendientes, CPA y carta de referencia.", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="K.26", modelo="Tebas A 3D 2B WC (18)", modeloBase="Tebas", cliente="Juan Carlos Peña Ramirez", montoCasa=16000000, loteAD=6926156, loteQFI=7844306.4, fecha="2026-03-23", banco="BP", formalizador="Hazel", vendedor="Daniela", traspaso=True, permisos="en trámite, en revisión de boleta electrónica en CFIA", capacidad="Cliente transportista independiente", pendientes="A espera de información del cliente, ya envió una parte, se hablo con el contador y dice esta preparando la información. .1", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="F.18", modelo="Ikaria A 2D 2B WC", modeloBase="Ikaria", cliente="Maria Auxiliadora Araya Céspedes", montoCasa=14000000, loteAD=7310057, loteQFI=7613965.8, fecha="2026-03-23", banco="Caja de Ande", formalizador="Hazel", vendedor="Randall", traspaso=True, permisos=True, capacidad="Maestra MEP, quiere el trámite con Caja de Ande, con otras entidades posiblemente sin capacidad", pendientes="Cliente quiere esperar condiciones de Expo, no ha enviado información.", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="K.25", modelo="Tebas A 3D 2B WC", modeloBase="Tebas", cliente="Josue David Montoya Chavarría", montoCasa=36000000, loteAD=8839195, loteQFI=9261982.8, fecha="2026-03-23", banco="Por definir", formalizador="Hazel", vendedor="Mery", traspaso=True, permisos=True, capacidad="cliente asalariado, de acuerdo con las colillas y sugef si tiene capacidad de pago", pendientes="Constancia y sicere del cliente", terminada=True, estadoCasa="Terminada"),

  dict(lote="M.05", modelo="Santorini A 3D 2.5B WC", modeloBase="Santorini", cliente="Silvia Salazar Sanchez", montoCasa=91000000, loteAD=6561241, loteQFI=9263255.4, fecha="2026-03-19", banco="BN", formalizador="Willem", vendedor="Marco", traspaso="FINALIZADO✅", permisos="FINALIZADO✅", capacidad="PAGAR Y CERRAR PROMERICA ¢8.000.000", pendientes="FINALIZADO✅", terminada=True, estadoCasa="Terminada"),
  dict(lote="L.32", modelo="Zante A 4D 2.5B WC (PA)", modeloBase="Zante", cliente="Mario Alexander Mena Barboza", montoCasa=22000000, loteAD=10839195, loteQFI=7896483, fecha="2026-03-12", banco="BN", formalizador="Willem", vendedor="Daniela", traspaso="FINALIZADO✅", permisos="FINALIZADO✅", capacidad="FINALIZADO / PUEDE VARIAR DEPENDIENDO BANCO", pendientes="ESPERAR CLIENTE SE DECIDA DE BANCO/ NO HA QUERIDO FIRMAR CONTRATOS PARA PEDIR AVALUO. Hoy ya me salio permiso, vamos a pedir presupuesto.", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="I.13", modelo="Zante T 2D 3.5B WC OF", modeloBase="Zante", cliente="Cristian Hidalgo Avila", montoCasa=22000000, loteAD=9226277.5, loteQFI=7664233.5, fecha="2026-04-10", banco="BN", formalizador="Willem", vendedor="Hannia", traspaso="FINALIZADO✅", permisos="FINALIZADO✅", capacidad="FINALIZADO✅", pendientes="CONTRATO LABORAL INDEFINIDO PLAZO, se lo dan hasta 1 abril", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="M.16", modelo="Stellita A 2D 1.5B WC", modeloBase="Stellita", cliente="Daniel Quiros Soto", montoCasa=14000000, loteAD=8605988, loteQFI=6836407.2, fecha="2026-03-12", banco="BN", formalizador="Willem", vendedor="Olman", traspaso="FINALIZADO✅", permisos="FINALIZADO✅", capacidad="FINALIZADO✅", pendientes="AVALUO (cambio modelo ) hoy en cambio de laminas, espero miércoles ya poder pedir avalúo", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="L.31", modelo="Stella A", modeloBase="Stella", cliente="Elizabeth Cano", montoCasa=22000000, loteAD=9226277.5, loteQFI=7664233.5, fecha="2026-03-31", banco="Promerica", formalizador="Willem", vendedor="Mery", traspaso=True, permisos="en cfia", capacidad="ok", pendientes="Cliente esperando tasas expo, según me dice la vendedora Mery", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="K.19", modelo="Stella A", modeloBase="Stella", cliente="Valeria Acosta", montoCasa=22000000, loteAD=9226277.5, loteQFI=7664233.5, fecha="2026-03-31", banco="BN", formalizador="Willem", vendedor="Daniela", traspaso="Hoy se solicita.", permisos="vamos a tramitarlo", capacidad="Clienta acaba de renunciar, entra al nuevo el 16 de este mes, gana ¢1.400.000 brutos, deuda ¢120.000, casa ¢92.000.000 lo veo ajustado.", pendientes="Vamos a esperar informacion para confirmar.", terminada=False, estadoCasa="Sin reunion de inicio"),

  dict(lote="L.33", modelo="Tebas T 3D 2D (17)", modeloBase="Tebas", cliente="Marcelly Alvarado Chaves", montoCasa=14000000, loteAD=8839195, loteQFI=7896483, fecha="2026-03-06", banco="Caja de Ande", formalizador="Luis Carlos", vendedor="Randall", traspaso=True, permisos=True, capacidad="Positiva ✅", pendientes="No hay", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="K.18", modelo="Ikaria T 2D 2B", modeloBase="Ikaria", cliente="Rafael Antonio Porras Castro", montoCasa=14000000, loteAD=6926156, loteQFI=7844306.4, fecha="2026-03-12", banco="BN", formalizador="Luis Carlos", vendedor="Xinia", traspaso=True, permisos=True, capacidad="Positiva ✅ BN", pendientes="valores avalúo", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="I.30", modelo="Stella T 2D 2.5B WC L", modeloBase="Stella", cliente="Isabel Jara Marín", montoCasa=22000000, loteAD=9560335, loteQFI=7463799, fecha="2026-03-23", banco="BN", formalizador="Luis Carlos", vendedor="Hannia", traspaso=True, permisos=True, capacidad="✅", pendientes="Contratos, formularios. Quiere esperar Expo", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="I.36", modelo="Zante T 4D 2.5B WC (PA)", modeloBase="Zante", cliente="Geiner Ulises Naranjo Romero", montoCasa=20000000, loteAD=9019480, loteQFI=7788312, fecha="2026-03-27", banco="BCR-MUCAP", formalizador="Luis Carlos", vendedor="Randall", traspaso=True, permisos=True, capacidad="Positiva", pendientes="Actualizar información, contratos, formularios. Cliente quiere esperar Expo", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="L.01", modelo="Stella A 3D 3.5B WC (PA)", modeloBase="Stella", cliente="Juan Daniel Arias Pérez", montoCasa=22000000, loteAD=9226277.5, loteQFI=7664233.5, fecha="2026-04-14", banco="BN-BCR-BP", formalizador="Luis Carlos", vendedor="Daniela", traspaso="No hay folios ni catastros", permisos="No hay folios ni catastros", capacidad="Trabaja para empresa del papá, debe aumentar salario y reportar a la CCSS", pendientes="Constancia, contratos, formularios", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="I.39", modelo="Santorini T", modeloBase="Santorini", cliente="Lohr Campbell Arguello", montoCasa=24000000, loteAD=8563362, loteQFI=9261982.8, fecha="2026-03-27", banco="BN", formalizador="Luis Carlos", vendedor="Irving", traspaso=True, permisos=True, capacidad="no se ha realizado", pendientes="Recopilando información", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="I.40", modelo="Santorini A 3D 2.5B WC", modeloBase="Santorini", cliente="Carolina Ureña Jimenez", montoCasa=25000000, loteAD=9563362, loteQFI=7964233.5, fecha="2026-03-28", banco="Mucap", formalizador="Luis Carlos", vendedor="Irving", traspaso=True, permisos="En proceso", capacidad="A espera de información del cliente", pendientes="Caso con Mucap, cliente con estados de cuenta pendientes, CPA y carta de referencia.", terminada=False, estadoCasa="Sin reunion de inicio"),

  dict(lote="K.05", modelo="Santorini A", modeloBase="Santorini", cliente="Joaquin Marin", montoCasa=22000000, loteAD=8618508, loteQFI=9228895.2, fecha="2026-03-12", banco="Promerica", formalizador="Esteban", vendedor="Randall", traspaso=True, permisos=True, capacidad="✅", pendientes="caso se encuentra en aprobación, pendiente avalúo, contra avalúo se pasa opción de compra, para cuadrar el número, en dólares.", terminada=False, estadoCasa="Sin reunion de inicio"),
  dict(lote="1-01 Barani", modelo="Santorini A", modeloBase="Santorini", cliente="Jose Arturo Campos", montoCasa=105000000, loteAD=0, loteQFI=11430493.2, fecha="2026-04-08", banco="Mucap", formalizador="Esteban", vendedor="Hannia", traspaso="Pendiente", permisos="Pendiente", capacidad="✅", pendientes="Escritura, Catastro, Traspaso, Permisos, Avalúo, pasar opción de compra en dolares", terminada=True, estadoCasa="Terminada"),
]

js_casas = json.dumps(casas, ensure_ascii=False, indent=2)
start = html.find('const casas = [')
end = html.find('];\n\n// Helpers', start)
if start != -1 and end != -1:
    html = html[:start] + 'const casas = ' + js_casas + ';\n\n// Helpers' + html[end + len('];\n\n// Helpers'):]

helpers = '''
const CLAVE_FECHA = "Adelante2025";

function renderEstadoSelect(c) {
  const options = ["Sin reunion de inicio", "Reunion de inicio", "Casa iniciada", "Terminada"];
  const current = c.estadoCasa || "Sin reunion de inicio";
  return `
    <select class="filter-select" style="width:auto"
      onchange="updateEstadoCasa('${c.lote}', this.value)">
      ${options.map(o => `<option value="${o}" ${current===o?'selected':''}>${o}</option>`).join('')}
    </select>
  `;
}

function updateEstadoCasa(lote, estado) {
  const casa = casas.find(c => c.lote === lote);
  if (!casa) return;
  casa.estadoCasa = estado;
  casa.terminada = (estado === "Terminada");
  applyFilters();
}

document.addEventListener('change', (e) => {
  if (!e.target.classList.contains('fecha-input')) return;
  const lote = e.target.dataset.lote;
  const nueva = e.target.value;
  const casa = casas.find(c => c.lote === lote);
  if (!casa) return;

  const clave = prompt('Ingrese la clave para modificar la fecha:');
  if (clave !== CLAVE_FECHA) {
    alert('Clave incorrecta. No se guardó el cambio.');
    e.target.value = casa.fecha;
    return;
  }
  casa.fecha = nueva;
  applyFilters();
});

function renderVendedor() {
  const groups = {};
  filteredData.forEach(c => {
    const key = c.vendedor || 'Sin vendedor';
    if (!groups[key]) groups[key] = [];
    groups[key].push(c);
  });
  let h = '<div class="form-grid">';
  for (const [name, items] of Object.entries(groups)) {
    const totalCasa = items.reduce((s, c) => s + c.montoCasa, 0);
    const terminadas = items.filter(c => c.terminada).length;
    h += `
      <div class="form-section">
        <div class="form-section-header">
          <span class="form-section-name" style="font-size:16px;padding:6px 14px;background:#E5E7EB;color:#374151;border-radius:6px">${name}</span>
          <div class="form-section-stats">
            <span>${items.length} casos</span>
            <span style="color:var(--success);font-weight:600">${terminadas} term.</span>
            <span style="color:var(--claude-dark);font-weight:700">${fmt(totalCasa)}</span>
          </div>
        </div>
        <div class="form-section-body">`;
    items.sort((a, b) => new Date(a.fecha) - new Date(b.fecha));
    items.forEach(c => {
      h += `
        <div class="form-case ${c.terminada ? 'terminada' : ''}">
          <div class="form-case-header">
            <span class="form-case-lote">${c.lote} ${c.terminada ? '<span class="terminada-badge">✓ TERMINADA</span>' : ''}</span>
            <span class="monto-highlight">${fmt(c.montoCasa)}</span>
          </div>
          <div class="form-case-client">${c.cliente} — ${c.modelo}</div>
          <div class="form-case-row">
            <span class="bank-tag">${c.banco}</span>
            <span style="font-size:12px;color:var(--text-secondary)">📅 ${formatDate(c.fecha)}</span>
            <span class="form-status-item">${renderTraspasoStatus(c.traspaso)} Traspaso</span>
            <span class="form-status-item">${renderPermisosStatus(c.permisos)} Permisos</span>
          </div>
          <div class="form-case-pendientes">📌 ${c.pendientes}</div>
        </div>`;
    });
    h += '</div></div>';
  }
  h += '</div>';
  document.getElementById('viewVendedor').innerHTML = h;
}

function renderTraspasoStatus(val) {
  if (val === true || (typeof val === 'string' && val.includes('✅'))) return '✅';
  return '⏳';
}
function renderPermisosStatus(val) {
  if (val === true || (typeof val === 'string' && val.includes('✅'))) return '✅';
  return '⏳';
}
'''

insert_point = html.find('// Init')
html = html[:insert_point] + helpers + '\n' + html[insert_point:]

# Filters logic
html = html.replace('const formalizadores = [...new Set(casas.map(c => c.formalizador))].sort();',
                    'const formalizadores = [...new Set(casas.map(c => c.formalizador))].sort();\n  const vendedores = [...new Set(casas.map(c => c.vendedor))].filter(Boolean).sort();')
needle = "formalizadores.forEach(f => { const o = document.createElement('option'); o.value = f; o.textContent = f; fF.appendChild(o); });"
html = html.replace(needle, needle + "\n\n  const fV = document.getElementById('filterVendedor');\n  vendedores.forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; fV.appendChild(o); });")
html = html.replace('const f = document.getElementById(\'filterFormalizador\').value;',
                    'const f = document.getElementById(\'filterFormalizador\').value;\n  const v = document.getElementById(\'filterVendedor\').value;\n  const st = document.getElementById(\'filterEstado\').value;')
html = html.replace('if (f && c.formalizador !== f) return false;',
                    'if (f && c.formalizador !== f) return false;\n    if (v && c.vendedor !== v) return false;\n    if (st && c.estadoCasa !== st) return false;')

# renderAll Hook
html = html.replace('renderFormalizador();', 'renderFormalizador();\n  renderVendedor();')

# UI elements for mixed types and layout
html = html.replace('${c.traspaso ? \'<span class="status-check">✅</span>\' : \'<span class="status-pending">⏳</span>\'}', '${renderTraspasoStatus(c.traspaso)}')
html = html.replace('${c.permisos ? \'<span class="status-check"> ✅</span>\' : \'<span class="status-pending"> ⏳</span>\'}', '${renderPermisosStatus(c.permisos)}')
html = html.replace('<div class="monto-lote">Lote: ${fmt(c.montoLote)}</div>', '<div class="monto-lote" style="font-size:10px">AD: ${fmt(c.loteAD)} | QFI: ${fmt(c.loteQFI)}</div>')

# clearFilters
html = html.replace('document.getElementById(\'filterModelo\').value = \'\';', 'document.getElementById(\'filterModelo\').value = \'\';\n  document.getElementById(\'filterVendedor\').value = \'\';\n  document.getElementById(\'filterEstado\').value = \'\';')

# KPIs
html = html.replace('const totalLotes = filteredData.reduce((s, c) => s + c.montoLote, 0);', 'const totalLotes = filteredData.reduce((s, c) => s + (c.loteAD || 0) + (c.loteQFI || 0), 0);')

# Export
html = html.replace('\'Desembolso Lote (₡)\': c.montoLote,', '\'Lote AD (₡)\': c.loteAD, \'Lote QFI (₡)\': c.loteQFI,')
html = html.replace('\'Desembolso Total (₡)\': c.montoCasa + c.montoLote,', '\'Desembolso Total (₡)\': c.montoCasa + (c.loteAD||0) + (c.loteQFI||0),')
html = html.replace('\'Formalizador\': c.formalizador,', '\'Formalizador\': c.formalizador, \'Vendedor\': c.vendedor, \'Estado Casa\': c.estadoCasa,')

Path('/data/.openclaw/workspace/informesad/cdv_formalizacion_marzo2026/index.html').write_text(html)
