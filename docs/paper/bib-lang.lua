-- Runs after citeproc. references.bib serves every language, so its descriptive fields
-- (howpublished, type, note) are written in English; in a French report they are rendered in
-- French here. Titles are left exactly as their sources publish them.

local fr = {
  { 'News report on the adoption of Loi', 'Article de presse sur l’adoption de la loi' },
  { 'Decree of 20 December 2012, published by the', 'Décret du 20 décembre 2012, publié par la' },
  { 'Source code and data repository', 'Dépôt du code source et des données' },
  { 'dataset of 1 August 2025', 'jeu de données du 1er août 2025' },
  { 'Dataset and repository', 'Jeu de données et dépôt' },
  { 'Software repository', 'Dépôt de logiciel' },
  { 'Database export', 'Export de base de données' },
  { 'Geofabrik extract', 'Extrait Geofabrik' },
  { 'Addressing sheet', 'Fiche d’adressage' },
  { 'arXiv preprint', 'Prépublication arXiv' },
  { 'UPU standard', 'Norme de l’UPU' },
  { 'White paper', 'Livre blanc' },
  { 'News report', 'Article de presse' },
  { 'Web service', 'Service web' },
  { 'Web page', 'Page web' },
  { 'Web site', 'Site web' },
  { 'Dataset', 'Jeu de données' },
}

local function words(s)
  local t = {}
  for w in s:gmatch('%S+') do t[#t + 1] = w end
  return t
end

for _, p in ipairs(fr) do p.from = words(p[1]) end

-- Does the phrase start at inlines[i]? Returns the index of its last Str and the punctuation
-- that followed the last word in that Str (for example the comma in "report,").
local function match(inl, i, from)
  local j = i
  for k, w in ipairs(from) do
    local el = inl[j]
    if not el or el.t ~= 'Str' then return nil end
    if k < #from then
      if el.text ~= w then return nil end
      local sp = inl[j + 1]
      if not sp or (sp.t ~= 'Space' and sp.t ~= 'SoftBreak') then return nil end
      j = j + 2
    else
      if el.text:sub(1, #w) ~= w then return nil end
      local rest = el.text:sub(#w + 1)
      if not rest:match('^%p*$') then return nil end
      return j, rest
    end
  end
end

local function translate(inl)
  local out, i = pandoc.List(), 1
  while i <= #inl do
    local done = false
    for _, p in ipairs(fr) do
      local last, rest = match(inl, i, p.from)
      if last then
        out:extend(pandoc.Inlines(p[2] .. rest))
        i, done = last + 1, true
        break
      end
    end
    if not done then
      out:insert(inl[i])
      i = i + 1
    end
  end
  return out
end

function Pandoc(doc)
  local lang = pandoc.utils.stringify(doc.meta.lang or '')
  if lang:sub(1, 2) ~= 'fr' then return nil end
  doc.blocks = doc.blocks:walk({
    Div = function(d)
      if d.identifier ~= 'refs' then return nil end
      return d:walk({ Inlines = translate })
    end,
  })
  return doc
end
