-- In the PDF a figure uses its vector PDF; the markdown on the web uses the SVG.
function Image(img)
  img.src = img.src:gsub('%.svg$', '.pdf')
  return img
end

local function latex(s)
  return pandoc.RawBlock('latex', s)
end

-- A heading is never left alone at the foot of a page, and an unnumbered chapter (data
-- availability, acknowledgements, references) sets the running head itself.
function Header(h)
  local out = { latex('\\needspace{' .. (h.level == 1 and 8 or 6) .. '\\baselineskip}'), h }
  if h.level == 1 and h.classes:includes('unnumbered') then
    table.insert(out, latex('\\markboth{' .. pandoc.utils.stringify(h) .. '}{}'))
  end
  return out
end

-- A short table is kept on one page: room for its caption, header and rows is reserved first,
-- counting a long cell as several lines.
function Table(t)
  local rows, lines = 0, 0
  for _, body in ipairs(t.bodies) do
    for _, row in ipairs(body.body) do
      rows = rows + 1
      local n = 1
      for _, cell in ipairs(row.cells) do
        n = math.max(n, math.ceil(#pandoc.utils.stringify(cell.contents) / 30))
      end
      lines = lines + n
    end
  end
  if rows <= 18 then
    return { latex('\\needspace{' .. math.ceil(1.15 * lines + 8) .. '\\baselineskip}'), t }
  end
end
