
## Guidelines

- Keep design lean. Use cards, wrapper divs and containers ONLY when necessary
- Keep style consistent across the code base
- Setup eslint and ensure green linter (not by disabling it, but by writing clean code)
- Keep files, functions and classes short, with a single purpose, on one abstraction layer. Split complex functionality when called for.
- Do not hallucinate features I did not ask for
- Keep copy and micro-copy short and to the point. Avoid waffling, avoid marketing speak, and avoid labelling everything with triple redundancy.

- WRITE CLEAN CODE!!!!! Linting issues are to be fixed by fixing the fucking issues, not by disabling the linter!!


## UI Design

- Use Tailwind and Daisy.UI components
- Understand [App.vue](src/app/App.vue): Note that the router view is already wrapped with a container and a flex layout. Do not wrap a page into another container or flex layout for no reason.
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
- For recurring complex styles, use `@apply` in `App.vue`.
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