## UI Design

- Use Tailwind and Daisy.UI components
- Do not wrap a page into recursive containers or flex layout for no reason.
- In general (barring special cases where it makes no sense), every page should have a `h1` on top
- Use wrapping components and especially cards sparingly, and only when needed.
- When using a card, give it classes `card` and `shadow`. Nothing else. No variation unless called for.
- If a card must have an hover effect because it's clickable, give it `transition-hover` and `hover:shadow-md`
- A `card` always must have a `card-body` where the content lives (this is Daisy UI syntax)
- A `card-title`, if existing, must be within `card-body`
- Prefer clean `grid` and `flex` layouts over `space-*`
- Use standard buttons unless special case calls for customization. Do not vary the size randomly unless called for
- Do not use gray text. If text must be dis-emphasized, use only and consistently `text-light`. Do not give it an `sm` size.
- Do not use excessive subheadings, redundant labels or little information widgets that the user does not care about. 
- Before implementing a component, look for similar components and copy their styles and/or approach.
- When setting margins, paddings, gaps and so on, prefer the size `1`, `2`, `4`, and `6`
- User color sparingly, and only for primary/important elements or those that must use color to communicate (e.g. a warning)
- Make sure any given layout works well on mobile and desktop!

- Use this pattern for form inputs:

```
<fieldset class="fieldset">
  <label for="page-title" class="label">Page title</label>
  <input
    type="text"
    name="page-title"
    class="input"
    placeholder="My awesome page"
  />
</fieldset>
```

- KEEP. IT. SIMPLE.