# State Management in React

## Brief

- Duration: 45 minutes
- Audience: 65% beginner / 35% advanced
- Ratio: 40% content / 60% code

## Opening Frame

Mixed cohort skewing beginner (65% beginner / 35% advanced). Default to scaffolding vocabulary (state, re-render, single source of truth) and using frequent comprehension checks, while inserting optional depth callouts and tradeoff discussions to keep the 35% advanced learners engaged. Move at a moderate pace early (local/derived state) and accelerate through Context and reducers, where advanced learners can absorb tradeoffs quickly.

## 1. Owning State Inside a Component with useState

Timing: 9 min (4 content / 5 code)

### Instructor Narration

Alright, let's kick off state management. Quick recall before we start: so far, every component we've built receives its data from the outside through props. Props are read-only inputs — the parent hands them down, the child renders them. That works beautifully for data that stays fixed for the life of that render.

But here's the question I want you to sit with: what happens when data has to *change* after the component has already rendered? Think of a like button. The count starts at zero, but when I click, it needs to become one, then two. Props can't help us here — a component can't reassign its own props, and even if it could, React wouldn't know to re-render. So we need something new.

That something is *state*. Let me give you the one-sentence definition I want you to hold onto for the rest of this class: state is data that changes over time and, when it changes, causes the component to re-render with the new value. Two halves to that definition — it changes, and changing it repaints the UI. Both matter.

So the mental split becomes: props are data passed *in* from a parent that the component doesn't own; state is data the component *owns* and controls itself. That ownership idea is what we call the single source of truth — for a piece of local state, one component holds the real value, and everything it shows is based on that one value.

Before we touch any syntax, let's pressure-test that distinction with three quick examples, because the 'prop or state?' instinct is the whole game here. Then we'll live-code a like button so you can see state actually mutate and trigger a re-render in front of you.

[After the live code] So now you've seen it: useState hands us a value and a setter, we never mutate the value directly, we call the setter, and React re-renders. And notice each piece of state is independent — count and the toggle didn't interfere with each other. Now, here's the catch that sets up our next segment: sometimes we're tempted to store a value in state when we could just *compute* it from state we already have. Storing something you can derive is actually a trap. That's exactly where we're headed next — derived state.

### Live Code

1. Create a LikeButton component and import useState from React.

```text
import { useState } from 'react';

function LikeButton() {
  return <button>Like</button>;
}
```

2. Declare a piece of state with useState, destructuring the value and its setter.

```text
function LikeButton() {
  const [count, setCount] = useState(0);
  return <button>Like ({count})</button>;
}
```

3. Wire up an onClick handler that calls the setter — reusing event-handler knowledge from before.

```text
function LikeButton() {
  const [count, setCount] = useState(0);
  return (
    <button onClick={() => setCount(count + 1)}>
      Like ({count})
    </button>
  );
}
```

4. Add a second, independent piece of state — a boolean toggle — to show state slices don't interfere.

```text
function LikeButton() {
  const [count, setCount] = useState(0);
  const [liked, setLiked] = useState(false);
  return (
    <div>
      <button onClick={() => setCount(count + 1)}>Like ({count})</button>
      <button onClick={() => setLiked(!liked)}>
        {liked ? '❤️ Liked' : '🤍 Not liked'}
      </button>
    </div>
  );
}
```

### Checks

- After the button renders as 'Like (0)', I write onClick={() => { setCount(count + 1); setCount(count + 1); }}. What does the display show after one click?

## 2. Computing Instead of Storing: Derived State

Timing: 7 min (3 content / 4 code)

### Instructor Narration

We just stored two independent state values—but what if one value can always be calculated from another? That's the question I want you to keep asking as your components grow. Here's the trap most people fall into. Say we're building a shopping cart. We've got a list of items in state—that's real, that's data the user changes. But we also want to show a running total and an item count. The instinct is: 'Those are values I display, so they must be state too.' So we call useState three times: one for the items, one for the total, one for the count. Feels organized, right? Watch what happens when we actually run it. When I add an item, the items array updates and the component re-renders—remember from the last segment, calling a setter triggers a re-render. But the total? It's stale. It shows the old number. Why? Because I only updated the items state; I never told the total setter about the change. Now I have to remember to manually sync total and count every single time items changes. Every add, every remove, every quantity edit. That's three places I can forget, three places bugs hide. This is what we call the redundant state anti-pattern: storing a value in state that could always be computed from other state. The fix is a mindset shift. The total isn't independent data—it's a function of the items. So instead of storing it, we compute it during render. Every time the component re-renders, we recalculate the total right there in the render body from the current items. It's impossible for it to go stale, because it's derived fresh every time. Let me refactor this live so you see how much cleaner it gets. For the advanced folks—yes, if that computation were genuinely expensive, you'd reach for useMemo. But that's an optimization, not the default. The default is: compute in render, and only memoize when you've measured a real cost.

### Live Code

1. Show the anti-pattern: three separate pieces of state that must be kept in sync.

```text
function Cart() {
  const [items, setItems] = useState([
    { id: 1, name: 'Book', price: 12 },
    { id: 2, name: 'Pen', price: 3 },
  ]);
  const [total, setTotal] = useState(15);
  const [itemCount, setItemCount] = useState(2);

  function addItem() {
    setItems([...items, { id: Date.now(), name: 'Mug', price: 8 }]);
    // BUG: total and itemCount are never updated here
  }

  return (
    <div>
      <p>Items: {itemCount}</p>
      <p>Total: ${total}</p>
      <button onClick={addItem}>Add Mug</button>
    </div>
  );
}
```

2. Refactor: delete the redundant state and compute the values in the render body.

```text
function Cart() {
  const [items, setItems] = useState([
    { id: 1, name: 'Book', price: 12 },
    { id: 2, name: 'Pen', price: 3 },
  ]);

  // Derived values — computed every render from items
  const itemCount = items.length;
  const total = items.reduce((sum, item) => sum + item.price, 0);

  function addItem() {
    setItems([...items, { id: Date.now(), name: 'Mug', price: 8 }]);
  }

  return (
    <div>
      <p>Items: {itemCount}</p>
      <p>Total: ${total}</p>
      <button onClick={addItem}>Add Mug</button>
    </div>
  );
}
```

3. Advanced callout: mention useMemo only where it matters.

```text
const total = useMemo(
  () => items.reduce((sum, item) => sum + item.price, 0),
  [items]
);
```

### Checks

- In the first version, after clicking 'Add Mug', the items array grew but 'Total: $15' didn't change. Why does the displayed total go stale?

## 3. Passing State Down: Prop Drilling and Its Limits

Timing: 8 min (3 content / 5 code)

### Instructor Narration

Now that state can be computed and stored, how do two distant components share it? Let's start with the manual way—the one React gives you out of the box.

Here's the situation. We've already used `useState` to own state inside a single component. But real apps aren't one component—they're trees. Say a piece of data lives at the top of your tree, and a component way down at the bottom needs it. How do they connect?

The first move is called 'lifting state up.' The idea: put the state in the closest common parent of every component that needs it. That parent becomes the single source of truth—same principle we saw with local state, just moved to a higher place in the tree. Then you hand the data down through props.

And this is where it gets interesting. To get data from the top to the bottom, you sometimes have to pass it through components in the middle that don't actually use it. They just receive a prop and immediately hand it off to their own children. We call those pass-through, or intermediate, components—and the pattern of threading a prop down through them is called prop drilling.

Let me build a small three-level tree so you can feel the friction, because that friction is exactly what motivates the next tool. Watch what the middle component is forced to do.

### Live Code

1. Create the top-level App component that owns the user state.

```text
function App() {
  const [user, setUser] = useState({ name: 'Ada' });
  return <Layout user={user} />;
}
```

2. Add the Layout component in the middle.

```text
function Layout({ user }) {
  // Layout doesn't use `user` at all...
  return (
    <div className="layout">
      <Header user={user} />
    </div>
  );
}
```

3. Add the Header component that actually consumes the prop.

```text
function Header({ user }) {
  return <h1>Welcome, {user.name}!</h1>;
}
```

4. Imagine scaling this. Point out what happens with more layers.

```text
// App -> Layout -> Sidebar -> Nav -> Menu -> Header
// every one of those must accept and forward `user`
// rename the prop? refactor every level. Add a new prop? touch every level.
```

### Checks

- In our tree, which component is the single source of truth for `user`, and which component is just a pass-through?

## 4. Sharing State Without Drilling: Context API

Timing: 11 min (4 content / 7 code)

### Instructor Narration

Remember the pass-through component that just relayed props? Let's delete those props entirely. In the last segment we lifted our user state up to the App component, and then we had to pass it down through Layout, which didn't even use it, just so Header could read it. That middle component is what we called a pass-through, and when your tree gets deeper, you end up threading the same prop through five or six components that don't care about it. That's the pain Context is designed to remove.

Here's the mental model. Context lets a component way up the tree publish a value, and any component below it—no matter how deep—can grab that value directly, without anyone in the middle passing it along. Think of it like a radio broadcast: the Provider is the station transmitting on a frequency, and the consumers are radios tuned to that frequency. Nobody in between has to relay the signal.

There are exactly three pieces to make Context work, and I want beginners to lock onto this vocabulary because it's the whole feature. First, createContext—that's the function that creates the channel itself. Second, the Provider—a component that comes with your context, and it holds the actual value you want to share, given to it through a value prop. Third, the useContext hook—that's how a component reads the current value off the channel. createContext makes the channel, Provider fills it, useContext reads it. Say that back to yourself.

Now let's refactor the exact example from a minute ago so you see the before-and-after directly. We'll keep our useState in App—the state lives in the same place, we're not moving where the truth is. We're only changing how it travels down. Watch how the props on Layout just disappear.

For our advanced folks, keep one thing in mind while we type: everything below a Provider re-renders when that value changes. Context has no built-in selective subscription—if the value object changes identity, every consumer re-renders. That's why Context is a great transport mechanism for things like the current user or a theme, but it is not, by itself, a full state-management library. It solves sharing, not update logic or render optimization. We'll come back to that.

### Live Code

1. Start from the prop-drilling code we already have and create the context in its own line at the top of the module.

```text
import { createContext, useContext, useState } from 'react';

const UserContext = createContext(null);
```

2. In App, wrap the tree in UserContext.Provider and hand the state to it through the value prop. Delete the user prop we were passing to Layout.

```text
function App() {
  const [user, setUser] = useState({ name: 'Ada' });

  return (
    <UserContext.Provider value={user}>
      <Layout />
    </UserContext.Provider>
  );
}
```

3. Delete the pass-through prop entirely from Layout so learners see the middle component get simpler.

```text
function Layout() {
  return (
    <div className="layout">
      <Header />
    </div>
  );
}
```

4. In Header, read the value directly with useContext.

```text
function Header() {
  const user = useContext(UserContext);
  return <h1>Welcome, {user.name}</h1>;
}
```

### Checks

- Name the three pieces that make Context work, and what each one does.

## 5. Structuring Complex Updates: useReducer

Timing: 10 min (4 content / 6 code)

### Instructor Narration

Our Context now holds the cart state, but look at what's happening: every time we want to update it, we're calling a different setter with slightly different logic scattered across our components. Add an item here, remove one there, clear it somewhere else. As the update rules get more complex, that sprawl becomes hard to reason about. Let's centralize all that update logic in one place.

The tool for this is a reducer. Before we touch any React, I want you to hold one mental model in your head: a reducer is just a plain function that takes the current state and an action, and returns the new state. That's it. `(state, action) => newState`. It's a pure function — same inputs, same output, no side effects. If you've ever used `Array.reduce`, this is the same idea: you fold a sequence of actions into an accumulated state.

The 'action' is just an object that describes what happened. By convention it has a `type` — like `'ADD_ITEM'` or `'REMOVE_ITEM'` — and often a payload with the data the action needs. Notice the shift in thinking: instead of components saying 'set the state to this specific value', they say 'here's what happened' and the reducer decides how state should change. That's what we mean by modeling state transitions — you enumerate the ways your state can change in one readable place.

Once we have that reducer function, React gives us the `useReducer` hook to wire it up. You call `useReducer(reducer, initialState)` and it hands you back the current `state` and a `dispatch` function. Instead of calling setters, you call `dispatch({ type: 'ADD_ITEM', product })`, and React runs your reducer to compute the next state and re-renders — same re-render behavior you already know from useState.

So when do you reach for useReducer over multiple useState calls? Rule of thumb: when several pieces of state change together, or when the next state depends on the previous state through non-trivial logic. A single value with simple updates? Keep useState. A cart with add, remove, quantity, and clear operations that interact? That's a reducer.

And here's the payoff that ties our whole class together — for the advanced folks especially: you can put that `dispatch` function into the Context we built earlier. Now any component in the tree can dispatch actions to update shared state, without prop drilling and without a tangle of setters. That combination — useReducer for structured updates plus Context for distribution — is essentially a hand-rolled version of the state libraries you'll meet later.

Let's refactor our cart to prove it out.

### Live Code

1. Write the reducer as a plain function first, outside any component.

```text
function cartReducer(state, action) {
  switch (action.type) {
    case 'ADD_ITEM':
      return { ...state, items: [...state.items, action.product] };
    case 'REMOVE_ITEM':
      return {
        ...state,
        items: state.items.filter(i => i.id !== action.id),
      };
    case 'CLEAR':
      return { ...state, items: [] };
    default:
      return state;
  }
}
```

2. Wire the reducer into the component with useReducer.

```text
import { useReducer } from 'react';

const initialCart = { items: [] };

function Cart() {
  const [state, dispatch] = useReducer(cartReducer, initialCart);
  // state.items is our current cart
}
```

3. Replace scattered setters with dispatch calls in event handlers.

```text
<button onClick={() => dispatch({ type: 'ADD_ITEM', product })}>
  Add
</button>
<button onClick={() => dispatch({ type: 'REMOVE_ITEM', id: product.id })}>
  Remove
</button>
<button onClick={() => dispatch({ type: 'CLEAR' })}>Clear cart</button>
```

4. Optional advanced tie-in: expose dispatch through the Context from the earlier segment.

```text
<CartContext.Provider value={{ state, dispatch }}>
  {children}
</CartContext.Provider>

// In any deep child:
const { dispatch } = useContext(CartContext);
dispatch({ type: 'ADD_ITEM', product });
```

### Checks

- Given state { items: [{id:1},{id:2}] } and action { type: 'REMOVE_ITEM', id: 1 }, what does the reducer return?

## Recap

Walk the escalation ladder in one slide: local useState → derive don't store → lift state up → avoid drilling with Context → structure updates with useReducer. Use a decision heuristic ('does this value change? is it computable? who needs it? how complex are its updates?') and cold-call 2–3 quick answers to confirm the mental model.

## Next

Assign a short exercise: refactor a prop-drilled mini-app to Context + useReducer. Point beginners to the React docs on useState/useContext and advanced learners to Context re-render performance and when to reach for external state libraries (Zustand/Redux) and useMemo/useCallback.
