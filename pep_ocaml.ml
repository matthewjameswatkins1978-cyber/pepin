type ty = Int | Bool | Str | Unit | Named of string | List of ty
type span = { lo:int; hi:int; line:int; column:int }
type token_kind = Id of string | Number of int64 | Text of string | Hole of string option | Sym of string | Eof
type token = { kind:token_kind; at:span }
type expr =
  | EInt of int64*span | EBool of bool*span | EStr of string*span
  | EName of string*span | EHole of string option*span
  | ECall of string*expr list*span | EBin of string*expr*expr*span | EUnary of string*expr*span | EList of expr list*span | EIf of expr*expr*expr*span
  | ERecord of string*(string*expr*span) list*span | EField of expr*string*span
  | EMatch of expr*match_arm list*span
and pattern = PWildcard of span | PBind of string*span | PConstructor of string*pattern list*span
and match_arm = { pattern:pattern; result:expr; arm_span:span }
type type_decl = RecordDecl of string*(string*ty*span) list*span | UnionDecl of string*(string*(ty list)*span) list*span
type stmt = SLet of string*ty option*expr*span | SVar of string*ty option*expr*span | SAssign of string*expr*span | SReturn of expr*span | SBlock of stmt list*span | SIf of expr*stmt list*stmt list*span | SFor of string*expr*stmt list*span | SWhile of expr*stmt list*span | SExpr of expr*span
type func = { fname:string; params:(string*ty*span) list; result:ty; body:stmt list; fspan:span }
type top = TopFun of func | TopStmt of stmt | TopType of type_decl
type program = top list
type error = { code:string; message:string; at:span; expected:ty option }
exception Error of error

let rec type_name = function Int->"Int" | Bool->"Bool" | Str->"Str" | Unit->"Unit" | Named n->n | List t->"List["^type_name t^"]"
let scalar_equality_type = function Int|Bool|Str|Unit->true|_->false
let mkspan lo hi line column = {lo;hi;line;column}
let fail code message at ?expected () = raise(Error {code;message;at;expected})
let json_string s =
  let b=Buffer.create (String.length s+8) in
  Buffer.add_char b '"';
  String.iter (fun c -> match c with
    | '"' -> Buffer.add_string b "\\\"" | '\\' -> Buffer.add_string b "\\\\"
    | '\n' -> Buffer.add_string b "\\n" | '\r' -> Buffer.add_string b "\\r"
    | '\t' -> Buffer.add_string b "\\t" | '\b' -> Buffer.add_string b "\\b"
    | '\012' -> Buffer.add_string b "\\f"
    | c when Char.code c < 0x20 -> Buffer.add_string b (Printf.sprintf "\\u%04x" (Char.code c))
    | c -> Buffer.add_char b c) s;
  Buffer.add_char b '"'; Buffer.contents b
let pos_json s = Printf.sprintf "{\"offset\":%d,\"line\":%d,\"column\":%d}" s.lo s.line s.column
let span_json s = Printf.sprintf "{\"start\":%s,\"endOffset\":%d}" (pos_json s) s.hi
let expr_span = function EInt(_,s)|EBool(_,s)|EStr(_,s)|EName(_,s)|EHole(_,s)|ECall(_,_,s)|EBin(_,_,_,s)|EUnary(_,_,s)|EList(_,s)|EIf(_,_,_,s)|ERecord(_,_,s)|EField(_,_,s)|EMatch(_,_,s)->s
let rec contains_empty_list = function
 |EList([],_) -> true
 |EList(items,_) -> List.exists contains_empty_list items
 |ECall(_,args,_) -> List.exists contains_empty_list args
 |EBin(_,left,right,_) -> contains_empty_list left || contains_empty_list right
 |EUnary(_,value,_) -> contains_empty_list value
 |EIf(condition,yes,no,_) -> contains_empty_list condition || contains_empty_list yes || contains_empty_list no
 |ERecord(_,fields,_) -> List.exists(fun(_,value,_)->contains_empty_list value)fields
 |EField(value,_,_) -> contains_empty_list value
 |EMatch(subject,arms,_) -> contains_empty_list subject || List.exists(fun (arm:match_arm)->contains_empty_list arm.result)arms
 |EInt _|EBool _|EStr _|EName _|EHole _ -> false
let stmt_span = function SLet(_,_,_,s)|SVar(_,_,_,s)|SAssign(_,_,s)|SReturn(_,s)|SBlock(_,s)|SIf(_,_,_,s)|SFor(_,_,_,s)|SWhile(_,_,s)|SExpr(_,s)->s
let is_digit c = c>='0'&&c<='9'
let is_alpha c = c>='a'&&c<='z'||c>='A'&&c<='Z'||c='_'
let is_alnum c = is_alpha c || is_digit c

let invalid_utf8_offset text =
  let length = String.length text in
  let continuation byte = byte land 0xc0 = 0x80 in
  let rec scan i =
    if i = length then None
    else
      let first = Char.code text.[i] in
      if first < 0x80 then scan (i + 1)
      else
        let width, minimum, initial_mask =
          if first >= 0xc0 && first <= 0xdf then 2, 0x80, 0x1f
          else if first >= 0xe0 && first <= 0xef then 3, 0x800, 0x0f
          else if first >= 0xf0 && first <= 0xf7 then 4, 0x10000, 0x07
          else 0, 0, 0
        in
        if width = 0 || i + width > length then Some i
        else
          let codepoint = ref (first land initial_mask) in
          let invalid = ref None in
          for j = 1 to width - 1 do
            let byte = Char.code text.[i + j] in
            if not (continuation byte) then (if !invalid = None then invalid := Some (i + j))
            else codepoint := (!codepoint lsl 6) lor (byte land 0x3f)
          done;
          match !invalid with
          | Some offset -> Some offset
          | None when !codepoint < minimum || !codepoint > 0x10ffff || !codepoint >= 0xd800 && !codepoint <= 0xdfff -> Some i
          | None -> scan (i + width)
  in
  scan 0

let invalid_utf8_span text offset =
  let line = ref 1 and column = ref 1 in
  for i = 0 to offset - 1 do
    if text.[i] = '\n' then (incr line; column := 1) else incr column
  done;
  mkspan offset (min (String.length text) (offset + 1)) !line !column

let lex source =
  (match invalid_utf8_offset source with
   | Some offset -> fail "PEP_INVALID_UTF8" "Source contains invalid UTF-8" (invalid_utf8_span source offset) ()
   | None -> ());
  let n=String.length source and i=ref 0 and line=ref 1 and col=ref 1 in
  let tokens=ref [] in
  let advance () = let c=source.[!i] in incr i; if c='\n' then (incr line;col:=1) else incr col; c in
  let add kind lo ln cl = tokens := {kind;at=mkspan lo !i ln cl} :: !tokens in
  let rec loop () =
    if !i>=n then tokens := {kind=Eof;at=mkspan !i !i !line !col} :: !tokens else
    let c=source.[!i] in
    if c=' '||c='\t'||c='\r'||c='\n' then (ignore(advance());loop())
    else if c='#' || c='/' && !i+1<n && source.[!i+1]='/' then (
      while !i<n && source.[!i]<>'\n' do ignore(advance()) done; loop())
    else let lo= !i and ln= !line and cl= !col in
    if is_alpha c then (
      ignore(advance()); while !i<n && is_alnum source.[!i] do ignore(advance()) done;
      let word=String.sub source lo (!i-lo) in
      if word="_" then add (Hole None) lo ln cl else add (Id word) lo ln cl; loop())
    else if is_digit c then (
      ignore(advance()); while !i<n && is_digit source.[!i] do ignore(advance()) done;
      let raw=String.sub source lo (!i-lo) in
      let value=try Int64.of_string raw with _->fail "PEP_INT_LITERAL_RANGE" "Integer literal is outside the supported Int range" (mkspan lo !i ln cl) () in
      add (Number value) lo ln cl; loop())
    else if c='"' then (
      ignore(advance()); let b=Buffer.create 16 in
      let rec string_loop () =
        if !i>=n then fail "PEP_UNTERMINATED_STRING" "Unterminated string literal" (mkspan lo !i ln cl) ();
        match advance() with
        | '"' -> ()
        | '\\' -> if !i>=n then fail "PEP_UNTERMINATED_STRING" "Unterminated escape" (mkspan lo !i ln cl) () else
          (match advance() with
           | 'n'->Buffer.add_char b '\n'|'r'->Buffer.add_char b '\r'|'t'->Buffer.add_char b '\t'
           | '0'->Buffer.add_char b '\000'|'\\'->Buffer.add_char b '\\'|'"'->Buffer.add_char b '"'
           | _->fail "PEP_INVALID_ESCAPE" "Unsupported string escape" (mkspan lo !i ln cl) ()); string_loop()
        | '\n' -> fail "PEP_NEWLINE_IN_STRING" "String literals cannot contain an unescaped newline" (mkspan lo !i ln cl) ()
        | c -> Buffer.add_char b c; string_loop()
      in string_loop(); add (Text(Buffer.contents b)) lo ln cl; loop())
    else if c='?' then (
      ignore(advance());
      if !i<n && is_alpha source.[!i] then (ignore(advance());while !i<n&&is_alnum source.[!i] do ignore(advance()) done;
        add (Hole(Some(String.sub source (lo+1) (!i-lo-1)))) lo ln cl)
      else add (Hole None) lo ln cl; loop())
    else if c='<' && !i+1<n && source.[!i+1]='=' then (ignore(advance());ignore(advance());add (Sym "<=") lo ln cl;loop())
    else if c='=' && !i+1<n && source.[!i+1]='=' then (ignore(advance());ignore(advance());add (Sym "==") lo ln cl;loop())
    else if c='!' && !i+1<n && source.[!i+1]='=' then (ignore(advance());ignore(advance());add (Sym "!=") lo ln cl;loop())
    else if c='&' && !i+1<n && source.[!i+1]='&' then (ignore(advance());ignore(advance());add (Sym "&&") lo ln cl;loop())
    else if c='|' && !i+1<n && source.[!i+1]='|' then (ignore(advance());ignore(advance());add (Sym "||") lo ln cl;loop())
    else if c='-' && !i+1<n && source.[!i+1]='>' then (ignore(advance());ignore(advance());add (Sym "->") lo ln cl;loop())
    else if c='=' && !i+1<n && source.[!i+1]='>' then (ignore(advance());ignore(advance());add (Sym "=>") lo ln cl;loop())
    else if List.mem c ['(';')';'{';'}';'[';']';',';':';';';'+';'-';'*';'/';'=';'.';'|';'&';'!'] then
      (ignore(advance());add (Sym(String.make 1 c)) lo ln cl;loop())
    else fail "PEP_UNEXPECTED_CHARACTER" (Printf.sprintf "Unexpected character %C" c) (mkspan lo (lo+1) ln cl) ()
  in loop(); Array.of_list(List.rev !tokens)

type parser = { ts:token array; mutable p:int; mutable record_literals_allowed:bool }
let peek p = p.ts.(p.p)
let take p = let t=peek p in p.p<-min (p.p+1) (Array.length p.ts-1);t
let at p = (peek p).at
let symbol p s = match (peek p).kind with Sym x when x=s->true|_->false
let keyword p s = match (peek p).kind with Id x when x=s->true|_->false
let accept_sym p s = if symbol p s then (ignore(take p);true) else false
let expect_sym p s = if not(accept_sym p s) then fail "PEP_PARSE_EXPECTED" ("Expected '"^s^"'") (at p) ()
let expect_id p = match take p with {kind=Id s;_}->s|t->fail "PEP_PARSE_NAME" "Expected a name" t.at ()
let rec parse_type p = match take p with
  |{kind=Id "Int";_}->Int |{kind=Id "Bool";_}->Bool |{kind=Id "Str";_}->Str |{kind=Id "Unit";_}->Unit
  |{kind=Id "List";_}->expect_sym p "[";let element=parse_type p in expect_sym p "]";List element
  |{kind=Id name;_}->Named name
  |t->fail "PEP_PARSE_TYPE" "Expected a type name" t.at ()
let combine a b = mkspan a.lo b.hi a.line a.column
let rec parse_pattern p =
  let first = take p in
  match first.kind with
  | Hole None -> PWildcard first.at
  | Id name when accept_sym p "(" ->
      let args = ref [] in
      if not (symbol p ")") then (args := [parse_pattern p]; while accept_sym p "," do args := !args @ [parse_pattern p] done);
      let ending = at p in expect_sym p ")";
      PConstructor (name, !args, combine first.at ending)
  | Id name -> PBind (name, first.at)
  | t -> fail "PEP_PARSE_PATTERN" "Expected a constructor pattern, binding, or wildcard" first.at ()
let parse_type_decl p =
  let start = (take p).at in
  let name = expect_id p in
  if accept_sym p "=" then (
    let variants = ref [] in
    let rec variant () =
      let ctor_token = peek p in
      let ctor = expect_id p in expect_sym p "(";
      let args = ref [] in
      if not (symbol p ")") then (args := [parse_type p]; while accept_sym p "," do args := !args @ [parse_type p] done);
      let ending = at p in expect_sym p ")";
      variants := (ctor, !args, combine ctor_token.at ending) :: !variants
    in
    variant (); while accept_sym p "|" do variant () done;
    let last = match !variants with (_,_,s)::_ -> s | [] -> at p in
    UnionDecl (name, List.rev !variants, combine start last)
  ) else (
    expect_sym p "{";
    let fields = ref [] in
    while not (symbol p "}") && (peek p).kind <> Eof do
      let field_token = peek p in let field = expect_id p in expect_sym p ":";
      let field_type = parse_type p in
      fields := (field, field_type, combine field_token.at p.ts.(p.p-1).at) :: !fields;
      ignore (accept_sym p ","); ignore (accept_sym p ";")
    done;
    let ending = at p in expect_sym p "}";
    RecordDecl (name, List.rev !fields, combine start ending)
  )
let rec parse_expr p min_prec =
  let first=take p in
  let lhs=match first.kind with
    |Number n->EInt(n,first.at)|Text s->EStr(s,first.at)|Hole h->EHole(h,first.at)
    |Id "true"->EBool(true,first.at)|Id "false"->EBool(false,first.at)
    |Sym "[" -> let items=ref [] in
        if not(symbol p "]") then (items := [parse_expr p 0]; while accept_sym p "," do if not(symbol p "]") then items := !items @ [parse_expr p 0] done);
        let ending=at p in expect_sym p "]"; EList(!items,combine first.at ending)
    |Sym "!" -> let rhs=parse_expr p 30 in EUnary("!",rhs,combine first.at (expr_span rhs))
    |Id "if" ->
        let previous=p.record_literals_allowed in p.record_literals_allowed<-false;
        let condition=parse_expr p 0 in p.record_literals_allowed<-previous;
        expect_sym p "{"; let yes=parse_expr p 0 in ignore(at p); expect_sym p "}";
        if not(keyword p "else") then fail "PEP_PARSE_ELSE" "Expected else after the true branch" (at p) ();
        ignore(take p); expect_sym p "{"; let no=parse_expr p 0 in let ending=at p in expect_sym p "}"; EIf(condition,yes,no,combine first.at ending)
    |Id "match" ->
        let previous = p.record_literals_allowed in p.record_literals_allowed <- false;
        let subject = parse_expr p 0 in p.record_literals_allowed <- previous;
        expect_sym p "{";
        let arms = ref [] in
        while not (symbol p "}") && (peek p).kind <> Eof do
          let pat = parse_pattern p in expect_sym p "=>";
          let result = parse_expr p 0 in
          arms := {pattern=pat;result;arm_span=combine (match pat with PWildcard s|PBind(_,s)|PConstructor(_,_,s)->s) (expr_span result)} :: !arms
        done;
        let ending = at p in expect_sym p "}";
        EMatch (subject, List.rev !arms, combine first.at ending)
    |Id name -> if accept_sym p "(" then (
        let args=ref [] in if not(symbol p ")") then (args:= [parse_expr p 0];while accept_sym p "," do args:= !args@[parse_expr p 0] done);
        let close=at p in expect_sym p ")"; ECall(name,!args,combine first.at close))
      else if p.record_literals_allowed && symbol p "{" && (peek p).at.line=first.at.line then (
        ignore (take p); let fields=ref [] in
        if not (symbol p "}") then (
          let field () = let ft=peek p in let field=expect_id p in expect_sym p ":"; let value=parse_expr p 0 in fields := !fields @ [(field,value,combine ft.at (expr_span value))] in
          field (); while accept_sym p "," do if not (symbol p "}") then field () done);
        let close=at p in expect_sym p "}"; ERecord(name,!fields,combine first.at close)
      ) else EName(name,first.at)
    |Sym "(" ->let e=parse_expr p 0 in let close=at p in expect_sym p ")";
        let s=combine first.at close in (match e with EInt(n,_)->EInt(n,s)|EBool(v,_)->EBool(v,s)|EStr(v,_)->EStr(v,s)|EName(n,_)->EName(n,s)|EHole(h,_)->EHole(h,s)|ECall(n,a,_)->ECall(n,a,s)|EBin(o,l,r,_)->EBin(o,l,r,s)|EUnary(o,x,_)->EUnary(o,x,s)|EList(xs,_)->EList(xs,s)|EIf(c,y,n,_)->EIf(c,y,n,s)|ERecord(n,f,_)->ERecord(n,f,s)|EField(e,n,_)->EField(e,n,s)|EMatch(e,a,_)->EMatch(e,a,s))
    |Sym "-" -> let rhs=parse_expr p 30 in EBin("neg",EInt(0L,first.at),rhs,combine first.at (expr_span rhs))
    |t->fail "PEP_PARSE_EXPRESSION" "Expected an expression" first.at () in
  parse_tail p min_prec lhs
and parse_tail p min_prec lhs =
  if symbol p "." then (ignore (take p); let field_token=peek p in let field=expect_id p in parse_tail p min_prec (EField(lhs,field,combine (expr_span lhs) field_token.at)))
  else let op,prec=match (peek p).kind with Sym "||"->"||",1|Sym "&&"->"&&",2|Sym "=="->"==",3|Sym "!="->"!=",3|Sym "<="->"<=",5|Sym "+"->"+",10|Sym "-"->"-",10|Sym "*"->"*",20|Sym "/"->"/",20|_->"",-1 in
  if prec<min_prec then lhs else (ignore(take p); let rhs=parse_expr p (prec+1) in parse_tail p min_prec (EBin(op,lhs,rhs,combine (expr_span lhs) (expr_span rhs))))
let rec parse_stmt p =
  let parse_body () =
    expect_sym p "{";
    let body=ref [] in
    while not(symbol p "}") && (peek p).kind<>Eof do body:=parse_stmt p :: !body done;
    let ending=at p in expect_sym p "}";
    List.rev !body,ending
  in
  if keyword p "let" || keyword p "var" then (
    let mutable_binding=keyword p "var" in let start=(take p).at in let name=expect_id p in
    let annotation=if accept_sym p ":" then Some(parse_type p) else None in
    expect_sym p "="; let value=parse_expr p 0 in ignore(accept_sym p ";");
    if mutable_binding then SVar(name,annotation,value,combine start (expr_span value))
    else SLet(name,annotation,value,combine start (expr_span value)))
  else if keyword p "return" then (
    let start=(take p).at in let value=parse_expr p 0 in ignore(accept_sym p ";");
    SReturn(value,combine start (expr_span value)))
  else if keyword p "if" then (
    let start=(take p).at in
    let previous=p.record_literals_allowed in p.record_literals_allowed<-false;
    let condition=parse_expr p 0 in p.record_literals_allowed<-previous;
    let yes,yes_end=parse_body () in
    if not(keyword p "else") then fail "PEP_PARSE_ELSE" "Expected else after if block" (at p) ();
    ignore(take p);let no,no_end=parse_body () in SIf(condition,yes,no,combine start no_end))
  else if keyword p "while" then (
    let start=(take p).at in
    let previous=p.record_literals_allowed in p.record_literals_allowed<-false;
    let condition=parse_expr p 0 in p.record_literals_allowed<-previous;
    let body,ending=parse_body () in SWhile(condition,body,combine start ending))
  else if keyword p "for" then (
    let start=(take p).at in let name=expect_id p in
    if not(keyword p "in") then fail "PEP_PARSE_FOR_IN" "Expected 'in' after the loop variable" (at p) ();
    ignore(take p);
    let previous=p.record_literals_allowed in p.record_literals_allowed<-false;
    let values=parse_expr p 0 in p.record_literals_allowed<-previous;
    let body,ending=parse_body () in
    SFor(name,values,body,combine start ending))
  else if symbol p "{" then (
    let start=(take p).at in let body=ref [] in
    while not(symbol p "}") && (peek p).kind<>Eof do body:=parse_stmt p :: !body done;
    let ending=at p in expect_sym p "}"; SBlock(List.rev !body,combine start ending))
  else (
    let e=parse_expr p 0 in
    match e with
    |EName(name,_) when accept_sym p "=" ->
        let value=parse_expr p 0 in let sp=combine (expr_span e) (expr_span value) in
        ignore(accept_sym p ";");SAssign(name,value,sp)
    |_->ignore(accept_sym p ";");SExpr(e,expr_span e))
let parse_func p =
  let start=(take p).at in let name=expect_id p in expect_sym p "(";
  let params=ref [] in
  if not(symbol p ")") then (
    let param () = let n=expect_id p in let ns=p.ts.(p.p-1).at in expect_sym p ":";let t=parse_type p in params:= !params@[(n,t,ns)] in
    param();while accept_sym p "," do param() done);
  expect_sym p ")"; expect_sym p "->"; let result=parse_type p in
  let body=match parse_stmt p with SBlock(xs,_)->xs|s->fail "PEP_FUNCTION_BODY" "Expected a braced function body" (stmt_span s) () in
  let ending=p.ts.(p.p-1).at in {fname=name;params= !params;result;body;fspan=combine start ending}
let parse source =
  let p={ts=lex source;p=0;record_literals_allowed=true} and tops=ref [] in
  while (peek p).kind<>Eof do
    if keyword p "fn" then tops:=TopFun(parse_func p)::!tops else if keyword p "type" then tops:=TopType(parse_type_decl p)::!tops else tops:=TopStmt(parse_stmt p)::!tops
  done; List.rev !tops

let parse_single_expression source =
  let p={ts=lex source;p=0;record_literals_allowed=true} in
  let expression=parse_expr p 0 in
  match (peek p).kind with
  | Eof -> expression
  | _ -> fail "PEP_REPLACEMENT_TRAILING_INPUT" "Replacement must contain exactly one expression" (peek p).at ()

type binding = { bid:int; bname:string; bty:ty option; bspan:span; mutable_:bool }
type signature = { fid:int; name:string; params:(string*ty) list; result:ty; decl:func }
type texpr = { node:texpr_node; ety:ty option; espan:span }
and texpr_node = XInt of int64|XBool of bool|XStr of string|XVar of int|XHole of string option|XCall of int option*string*texpr list|XBin of string*texpr*texpr|XUnary of string*texpr|XList of texpr list|XIf of texpr*texpr*texpr
  | XRecord of int*(int*texpr) list | XField of int*texpr | XConstructor of int*int*string*texpr list | XMatch of texpr*tmatch_arm list
and tpattern = TPWildcard of span | TPBind of binding | TPConstructor of int*tpattern list*span
and tmatch_arm = { tpattern:tpattern; tresult:texpr }
type tstmt = TLet of binding*texpr|TVar of binding*texpr|TAssign of binding*texpr*span|TReturn of texpr|TBlock of tstmt list|TIf of texpr*tstmt list*tstmt list*span|TFor of binding*texpr*tstmt list*span|TWhile of texpr*tstmt list*span|TExpr of texpr
type tfunc = { sig_:signature; tparams:binding list; tbody:tstmt list }
type hole = { hid:string option; hscope:string; hty:ty option; hspan:span; hbindings:binding list }
type record_info = { record_id:int; record_name:string; record_fields:(int*string*ty*span) list; record_span:span }
type union_info = { union_id:int; union_name:string; union_variants:(int*string*ty list*span) list; union_span:span }
type checked = { functions:tfunc list; tops:tstmt list; holes:hole list; records:record_info list; unions:union_info list }

let semantic_record_info id name base fields =
  { record_id=id; record_name=name;
    record_fields=List.mapi (fun index (field,field_type) -> base-index,field,field_type,mkspan 0 0 1 1) fields;
    record_span=mkspan 0 0 1 1 }

let semantic_record_infos = [
  semantic_record_info (-1) "FunctionInfo" (-101) ["id",Int;"name",Str;"startByte",Int;"endByte",Int];
  semantic_record_info (-2) "CallEdge" (-201) ["caller",Int;"callee",Int];
  semantic_record_info (-3) "SemanticDiagnostic" (-301) ["code",Str;"message",Str;"startByte",Int;"endByte",Int];
  semantic_record_info (-4) "ProgramInfo" (-401)
    ["document",Str;"revision",Str;"status",Str;"functions",List(Named "FunctionInfo");
     "calls",List(Named "CallEdge");"roots",List Int;"diagnostics",List(Named "SemanticDiagnostic")]
]
let lookup env name = let rec go=function []->None|scope::rest->match List.find_opt(fun b->b.bname=name)scope with Some b->Some b|None->go rest in go env
let has_current env name = match env with scope::_->List.exists(fun b->b.bname=name)scope|[]->false
let visible env =
  let seen=Hashtbl.create 8 in
  List.concat_map (fun scope->List.filter(fun b->if Hashtbl.mem seen b.bname then false else (Hashtbl.add seen b.bname ();true)) scope) env
let candidates ty bs=List.filter(fun b->b.bty=Some ty)bs
let rec ast_expr_json e = let s=span_json(expr_span e) in match e with
 |EInt(n,_)->"{\"kind\":\"int\",\"value\":"^Int64.to_string n^",\"span\":"^s^"}"
 |EBool(v,_)->"{\"kind\":\"bool\",\"value\":"^string_of_bool v^",\"span\":"^s^"}"
 |EStr(v,_)->"{\"kind\":\"string\",\"value\":"^json_string v^",\"span\":"^s^"}"
 |EName(n,_)->"{\"kind\":\"name\",\"name\":"^json_string n^",\"span\":"^s^"}"
 |EHole(h,_)->"{\"kind\":\"hole\",\"name\":"^(match h with None->"null"|Some x->json_string x)^",\"span\":"^s^"}"
 |ECall(n,args,_)->"{\"kind\":\"call\",\"name\":"^json_string n^",\"arguments\":["^String.concat ","(List.map ast_expr_json args)^"],\"span\":"^s^"}"
 |EBin(o,a,b,_)->"{\"kind\":\"binary\",\"operator\":"^json_string o^",\"left\":"^ast_expr_json a^",\"right\":"^ast_expr_json b^",\"span\":"^s^"}"
 |EUnary(o,x,_)->"{\"kind\":\"unary\",\"operator\":"^json_string o^",\"operand\":"^ast_expr_json x^",\"span\":"^s^"}"
 |EList(xs,_)->"{\"kind\":\"list\",\"elements\":["^String.concat ","(List.map ast_expr_json xs)^"],\"span\":"^s^"}"
 |EIf(c,y,n,_)->"{\"kind\":\"if\",\"condition\":"^ast_expr_json c^",\"then\":"^ast_expr_json y^",\"else\":"^ast_expr_json n^",\"span\":"^s^"}"
 |ERecord(n,fields,_)->"{\"kind\":\"record\",\"typeName\":"^json_string n^",\"fields\":["^String.concat "," (List.map(fun(name,e,sp)->"{\"name\":"^json_string name^",\"value\":"^ast_expr_json e^",\"span\":"^span_json sp^"}") fields)^"] ,\"span\":"^s^"}"
 |EField(e,n,_)->"{\"kind\":\"field_access\",\"value\":"^ast_expr_json e^",\"field\":"^json_string n^",\"span\":"^s^"}"
 |EMatch(e,arms,_)->"{\"kind\":\"match\",\"value\":"^ast_expr_json e^",\"arms\":["^String.concat "," (List.map(fun arm->"{\"pattern\":"^ast_pattern_json arm.pattern^",\"result\":"^ast_expr_json arm.result^",\"span\":"^span_json arm.arm_span^"}") arms)^"] ,\"span\":"^s^"}"
and ast_pattern_json = function
 |PWildcard sp->"{\"kind\":\"wildcard_pattern\",\"span\":"^span_json sp^"}"
 |PBind(n,sp)->"{\"kind\":\"binding_pattern\",\"name\":"^json_string n^",\"span\":"^span_json sp^"}"
 |PConstructor(n,args,sp)->"{\"kind\":\"constructor_pattern\",\"name\":"^json_string n^",\"arguments\":["^String.concat "," (List.map ast_pattern_json args)^"] ,\"span\":"^span_json sp^"}"
let rec ast_stmt_json s=match s with
 |SLet(n,t,e,sp)->"{\"kind\":\"let\",\"name\":"^json_string n^",\"annotation\":"^(match t with None->"null"|Some t->json_string(type_name t))^",\"value\":"^ast_expr_json e^",\"span\":"^span_json sp^"}"
 |SVar(n,t,e,sp)->"{\"kind\":\"var\",\"name\":"^json_string n^",\"annotation\":"^(match t with None->"null"|Some t->json_string(type_name t))^",\"value\":"^ast_expr_json e^",\"span\":"^span_json sp^"}"
 |SAssign(n,e,sp)->"{\"kind\":\"assignment\",\"name\":"^json_string n^",\"value\":"^ast_expr_json e^",\"span\":"^span_json sp^"}"
 |SReturn(e,sp)->"{\"kind\":\"return\",\"value\":"^ast_expr_json e^",\"span\":"^span_json sp^"}"
 |SBlock(xs,sp)->"{\"kind\":\"block\",\"statements\":["^String.concat ","(List.map ast_stmt_json xs)^"],\"span\":"^span_json sp^"}"
 |SIf(c,y,n,sp)->"{\"kind\":\"if_statement\",\"condition\":"^ast_expr_json c^",\"then\":["^String.concat ","(List.map ast_stmt_json y)^"],\"else\":["^String.concat ","(List.map ast_stmt_json n)^"],\"span\":"^span_json sp^"}"
 |SFor(name,values,body,sp)->"{\"kind\":\"for_in\",\"name\":"^json_string name^",\"iterable\":"^ast_expr_json values^",\"body\":["^String.concat ","(List.map ast_stmt_json body)^"],\"span\":"^span_json sp^"}"
 |SWhile(c,body,sp)->"{\"kind\":\"while\",\"condition\":"^ast_expr_json c^",\"body\":["^String.concat ","(List.map ast_stmt_json body)^"],\"span\":"^span_json sp^"}"
 |SExpr(e,sp)->"{\"kind\":\"expression\",\"value\":"^ast_expr_json e^",\"span\":"^span_json sp^"}"
let ast_json tops = "["^String.concat ","(List.map(function
 |TopFun f->"{\"kind\":\"function\",\"name\":"^json_string f.fname^",\"parameters\":["^String.concat ","(List.map(fun(n,t,s)->"{\"name\":"^json_string n^",\"type\":"^json_string(type_name t)^",\"span\":"^span_json s^"}")f.params)^"],\"returnType\":"^json_string(type_name f.result)^",\"body\":["^String.concat ","(List.map ast_stmt_json f.body)^"],\"span\":"^span_json f.fspan^"}"
 |TopStmt s->ast_stmt_json s
 |TopType (RecordDecl(n,fields,sp))->"{\"kind\":\"record_declaration\",\"name\":"^json_string n^",\"fields\":["^String.concat "," (List.map(fun(field,t,fs)->"{\"name\":"^json_string field^",\"type\":"^json_string(type_name t)^",\"span\":"^span_json fs^"}") fields)^"] ,\"span\":"^span_json sp^"}"
 |TopType (UnionDecl(n,variants,sp))->"{\"kind\":\"union_declaration\",\"name\":"^json_string n^",\"variants\":["^String.concat "," (List.map(fun(name,types,vs)->"{\"name\":"^json_string name^",\"arguments\":["^String.concat "," (List.map(fun t->json_string(type_name t)) types)^"] ,\"span\":"^span_json vs^"}") variants)^"] ,\"span\":"^span_json sp^"}")tops)^"]"

let check tops =
  let next_id=ref 0 and next_fid=ref 0 and next_type_id=ref 0 and next_field_id=ref 0 and next_ctor_id=ref 0 and holes=ref [] in
  let fresh ()=let n= !next_id in incr next_id;n in
  let fresh_type ()=let n= !next_type_id in incr next_type_id;n in
  let fresh_field ()=let n= !next_field_id in incr next_field_id;n in
  let fresh_ctor ()=let n= !next_ctor_id in incr next_ctor_id;n in
  let type_table=Hashtbl.create 16 and constructor_table=Hashtbl.create 32 in
  let records=ref [] and unions=ref [] in
  List.iter (fun info -> Hashtbl.add type_table info.record_name (`Record info)) semantic_record_infos;
  List.iter(function
    |TopType (RecordDecl(name,fields,sp))->
        if List.mem name ["Int";"Bool";"Str";"Unit";"List"] || Hashtbl.mem type_table name then fail "PEP_DUPLICATE_TYPE" ("Duplicate or reserved type '"^name^"'") sp ();
        let ids=Hashtbl.create 8 in
        let resolved=List.map(fun(field,ty,fsp)->if Hashtbl.mem ids field then fail "PEP_DUPLICATE_FIELD" ("Duplicate field '"^field^"'") fsp ();Hashtbl.add ids field ();fresh_field(),field,ty,fsp) fields in
        let info={record_id=fresh_type();record_name=name;record_fields=resolved;record_span=sp} in
        Hashtbl.add type_table name (`Record info); records:=info::!records
    |TopType (UnionDecl(name,variants,sp))->
        if List.mem name ["Int";"Bool";"Str";"Unit";"List"] || Hashtbl.mem type_table name then fail "PEP_DUPLICATE_TYPE" ("Duplicate or reserved type '"^name^"'") sp ();
        let ctor_ids=Hashtbl.create 8 in
        let resolved=List.map(fun(ctor,args,csp)->
          if List.mem ctor ["say";"int_text";"length";"append";"prepend";"reverse";"contains";"byte_length";"byte_at";"byte_slice";"semantic_snapshot";"source_bytes"] then fail "PEP_RESERVED_CONSTRUCTOR" ("Constructor name '"^ctor^"' is reserved for a builtin") csp ();
          if Hashtbl.mem ctor_ids ctor || Hashtbl.mem constructor_table ctor then fail "PEP_DUPLICATE_CONSTRUCTOR" ("Duplicate constructor '"^ctor^"'") csp ();
          Hashtbl.add ctor_ids ctor ();
          let item=(fresh_ctor(),ctor,args,csp) in Hashtbl.add constructor_table ctor (name,item); item) variants in
        let info={union_id=fresh_type();union_name=name;union_variants=resolved;union_span=sp} in
        Hashtbl.add type_table name (`Union info); unions:=info::!unions
    |_->()) tops;
  let rec valid_type ty sp = match ty with
    |Named name when not (Hashtbl.mem type_table name) -> fail "PEP_UNKNOWN_TYPE" ("Unknown type '"^name^"'") sp ()
    |List element -> valid_type element sp
    |_ -> () in
  List.iter (function
    |TopType (RecordDecl(_,fields,_))->List.iter(fun(_,ty,sp)->valid_type ty sp) fields
    |TopType (UnionDecl(_,variants,_))->List.iter(fun(_,args,sp)->List.iter(fun ty->valid_type ty sp) args) variants
    |TopFun f->List.iter(fun(_,ty,sp)->valid_type ty sp)f.params;valid_type f.result f.fspan
    |TopStmt _->()) tops;
  List.iter(fun info->List.iter(fun(_,_,args,sp)->List.iter(fun ty->valid_type ty sp) args) info.union_variants)!unions;
  let signatures=Hashtbl.create 16 in
  List.iter(function TopFun f->if List.mem f.fname ["say";"int_text";"length";"append";"prepend";"reverse";"contains";"byte_length";"byte_at";"byte_slice";"semantic_snapshot";"source_bytes"] || Hashtbl.mem constructor_table f.fname then fail "PEP_RESERVED_FUNCTION" ("Function name "^f.fname^" is reserved for a builtin or constructor") f.fspan () else if Hashtbl.mem signatures f.fname then fail "PEP_DUPLICATE_FUNCTION" ("Duplicate function '"^f.fname^"'") f.fspan () else
    let fid= !next_fid in incr next_fid;Hashtbl.add signatures f.fname {fid;name=f.fname;params=List.map(fun(n,t,_)->n,t)f.params;result=f.result;decl=f}
    |_->())tops;
  let record_hole env scope id expected sp = holes:={hid=id;hscope=scope;hty=expected;hspan=sp;hbindings=visible env}::!holes in
  let rec pattern_covers expected pat = match pat with
    |PWildcard _|PBind _->true
    |PConstructor(name,args,_) ->
        (match Hashtbl.find_opt constructor_table name with
         |Some(owner,(_,_,arg_types,_)) when expected=Named owner ->
             (match Hashtbl.find_opt type_table owner with
              |Some (`Union info)->List.length info.union_variants=1 && List.length args=List.length arg_types && List.for_all2 pattern_covers arg_types args
              |_->false)
         |_->false)
  in
  let rec check_pattern local expected pat = match pat with
    |PWildcard sp -> TPWildcard sp,true
    |PBind(name,sp) ->
        if List.exists(fun b->b.bname=name)!local then fail "PEP_DUPLICATE_PATTERN_BINDING" ("Duplicate pattern binding '"^name^"'") sp ();
        let b={bid=fresh();bname=name;bty=Some expected;bspan=sp;mutable_=false} in local:=b::!local;TPBind b,true
    |PConstructor(name,args,sp) ->
        let owner,(cid,_,arg_types,_) = match Hashtbl.find_opt constructor_table name with
          |None->fail "PEP_UNKNOWN_CONSTRUCTOR" ("Unknown constructor '"^name^"'") sp ()
          |Some pair->pair in
        if expected<>Named owner then fail "PEP_PATTERN_TYPE_MISMATCH" ("Constructor '"^name^"' belongs to "^owner^", not "^type_name expected) sp ~expected () ;
        if List.length args<>List.length arg_types then fail "PEP_PATTERN_ARITY" (Printf.sprintf "Constructor '%s' pattern expects %d argument(s), found %d" name (List.length arg_types) (List.length args)) sp ();
        let checked=List.map2(fun arg ty->check_pattern local ty arg)args arg_types in
        let irrefutable=pattern_covers expected pat in
        TPConstructor(cid,List.map fst checked,sp),irrefutable
  in
  let rec synth env scope e = match e with
   |EInt(n,s)->{node=XInt n;ety=Some Int;espan=s}
   |EBool(v,s)->{node=XBool v;ety=Some Bool;espan=s}
   |EStr(v,s)->{node=XStr v;ety=Some Str;espan=s}
   |EList(items,s)->list_expr env scope None items s
   |EUnary("!",value,s)->let checked=check_expr env scope (Some Bool) value in {node=XUnary("!",checked);ety=Some Bool;espan=s}
   |EUnary(operator,_,s)->fail "PEP_UNKNOWN_UNARY_OPERATOR" ("Unsupported unary operator '"^operator^"'") s ()
   |EHole(id,s)->record_hole env scope id None s;{node=XHole id;ety=None;espan=s}
   |EName(n,s)->(match lookup env n with None->fail "PEP_UNKNOWN_VARIABLE" ("Unknown variable '"^n^"'") s ()
      |Some b->(match b.bty with None->fail "PEP_UNCONSTRAINED_BINDING" ("Binding '"^n^"' has no known type") s ()
        |Some t->{node=XVar b.bid;ety=Some t;espan=s}))
   |ECall(n,args,s)->call env scope n args s
   |ERecord(name,fields,s)->
      let info=match Hashtbl.find_opt type_table name with Some (`Record info)->info |Some (`Union _)->fail "PEP_NOT_A_RECORD" ("Type '"^name^"' is not a record") s () |None->fail "PEP_UNKNOWN_TYPE" ("Unknown record type '"^name^"'") s () in
      let supplied=Hashtbl.create 8 in
      List.iter(fun(field,_,fsp)->if Hashtbl.mem supplied field then fail "PEP_DUPLICATE_FIELD" ("Duplicate field '"^field^"'") fsp ();Hashtbl.add supplied field ()) fields;
      List.iter(fun(_,field,_,fsp)->if not(Hashtbl.mem supplied field) then fail "PEP_MISSING_FIELD" ("Missing field '"^field^"'") fsp ()) info.record_fields;
      List.iter(fun(field,_,fsp)->if not(List.exists(fun(_,known,_,_)->known=field)info.record_fields) then fail "PEP_UNKNOWN_FIELD" ("Unknown field '"^field^"' on "^name) fsp ()) fields;
      let checked=List.map(fun(field,value,_)->let fid,_,ty,_=List.find(fun(_,known,_,_)->known=field)info.record_fields in fid,check_expr env scope (Some ty) value)fields in
      {node=XRecord(info.record_id,checked);ety=Some(Named name);espan=s}
   |EField(target,name,s)->
      let checked=synth env scope target in
      (match checked.ety with
       |Some (Named type_name)->(match Hashtbl.find_opt type_table type_name with
          |Some (`Record info)->(match List.find_opt(fun(_,field,_,_)->field=name)info.record_fields with
            |Some(fid,_,ty,_)->{node=XField(fid,checked);ety=Some ty;espan=s}
            |None->fail "PEP_UNKNOWN_FIELD" ("Record '"^type_name^"' has no field '"^name^"'") s ())
          |_->fail "PEP_FIELD_ON_NON_RECORD" ("Type '"^type_name^"' has no fields") s ())
       |Some ty->fail "PEP_FIELD_ON_NON_RECORD" ("Type '"^type_name ty^"' has no fields") s ()
       |None->fail "PEP_FIELD_ON_UNTYPED_VALUE" "Cannot access a field on an expression without a known type" s ())
   |EMatch(subject,arms,s)->match_expr env scope None subject arms s
   |EBin("<=",a,b,s)->let ta=check_expr env scope (Some Int) a and tb=check_expr env scope (Some Int) b in
      {node=XBin("<=",ta,tb);ety=Some Bool;espan=s}
   |EBin(("&&"|"||") as op,a,b,s)->let ta=check_expr env scope (Some Bool) a and tb=check_expr env scope (Some Bool) b in
      {node=XBin(op,ta,tb);ety=Some Bool;espan=s}
   |EBin(("=="|"!=") as op,a,b,s)->
      let ta=synth env scope a in
      let equality_type=match ta.ety with
        |Some ty when scalar_equality_type ty->ty
        |Some ty->fail "PEP_EQUALITY_UNSUPPORTED" ("Equality is not defined for "^type_name ty) (expr_span a) ()
        |None->fail "PEP_EQUALITY_UNTYPED" "Equality requires a typed left operand" (expr_span a) () in
      let tb=check_expr env scope (Some equality_type) b in
      {node=XBin(op,ta,tb);ety=Some Bool;espan=s}
   |EBin(op,a,b,s)->let ta=check_expr env scope (Some Int) a and tb=check_expr env scope (Some Int) b in
      {node=XBin(op,ta,tb);ety=Some Int;espan=s}
   |EIf(c,y,n,s)->let tc=check_expr env scope (Some Bool) c in
      let then_expr,else_expr=match y,n with
       |EHole _,EHole _->synth env scope y,synth env scope n
       |EHole _,_->let el=synth env scope n in check_expr env scope el.ety y,el
       |_,EHole _->let th=synth env scope y in th,check_expr env scope th.ety n
       |_->let th=synth env scope y in th,check_expr env scope th.ety n in
      (match then_expr.ety,else_expr.ety with Some a,Some b when a<>b->fail "PEP_TYPE_MISMATCH" ("If branches have types "^type_name a^" and "^type_name b) s ()|_->());
      {node=XIf(tc,then_expr,else_expr);ety=(match then_expr.ety with Some _ as t->t|None->else_expr.ety);espan=s}
  and list_expr env scope expected_element items sp =
    let element_type=match expected_element with Some ty->Some ty|None->
      let saved_holes= !holes in holes:=[];
      let rec find = function
        |[]->None
        |EHole _::rest|EList([],_)::rest->find rest
        |item::rest->match (synth env scope item).ety with Some ty->Some ty|None->find rest
      in
      let inferred=try find items with error->holes:=saved_holes;raise error in
      holes:=saved_holes;inferred
    in
    match element_type,items with
    |None,[]->fail "PEP_EMPTY_LIST_NEEDS_TYPE" "An empty list needs an expected List element type" sp ()
    |None,_->
      if List.exists contains_empty_list items then fail "PEP_EMPTY_LIST_NEEDS_TYPE" "An empty list needs an expected List element type" sp ();
      let checked=List.map(synth env scope)items in {node=XList checked;ety=None;espan=sp}
    |Some ty,_->let checked=List.map(check_expr env scope (Some ty))items in {node=XList checked;ety=Some(List ty);espan=sp}
  and check_expr env scope expected e = match e with
   |EList(items,sp)->(match expected with Some(List ty)->list_expr env scope (Some ty) items sp|_->list_expr env scope None items sp)
   |EHole(id,s)->record_hole env scope id expected s;{node=XHole id;ety=expected;espan=s}
   |EIf(c,y,n,s)->let tc=check_expr env scope (Some Bool) c in let ty=check_expr env scope expected y and en=check_expr env scope expected n in
      (match ty.ety,en.ety with Some a,Some b when a<>b->fail "PEP_TYPE_MISMATCH" ("If branches have types "^type_name a^" and "^type_name b) s ()|_->());
      {node=XIf(tc,ty,en);ety=(match expected with Some _ as t->t|None->(match ty.ety with Some _ as t->t|None->en.ety));espan=s}
   |EMatch(subject,arms,s)->match_expr env scope expected subject arms s
   |_->let t=synth env scope e in (match expected,t.ety with Some want,Some got when want<>got->fail "PEP_TYPE_MISMATCH" ("Expected "^type_name want^" but found "^type_name got) t.espan ~expected:want ()|_->());t
  and call env scope name args s =
    match Hashtbl.find_opt constructor_table name with
    |Some (owner,(cid,_,params,_))->
       if List.length args<>List.length params then fail "PEP_ARGUMENT_COUNT" (Printf.sprintf "Constructor '%s' expects %d argument(s), found %d" name (List.length params) (List.length args)) s ();
       let checked=List.map2(fun arg ty->check_expr env scope (Some ty) arg) args params in
       let uid=match Hashtbl.find type_table owner with `Union info->info.union_id|_->assert false in
       {node=XConstructor(uid,cid,name,checked);ety=Some(Named owner);espan=s}
    |None->
       let check_arity expected =
         if List.length args<>expected then fail "PEP_ARGUMENT_COUNT" (Printf.sprintf "Builtin '%s' expects %d argument(s), found %d" name expected (List.length args)) s ()
       in
       let list_argument expression =
         let checked=synth env scope expression in
         match checked.ety with
         |Some(List element)->checked,element
         |Some ty->fail "PEP_LIST_EXPECTED" (Printf.sprintf "Builtin '%s' expects a List, found %s" name (type_name ty)) (expr_span expression) ()
         |None->fail "PEP_LIST_UNTYPED" (Printf.sprintf "Builtin '%s' requires a list with a known element type" name) (expr_span expression) ()
       in
       if name="length" then (
         check_arity 1;
         let collection,_=list_argument (List.hd args) in
         {node=XCall(None,name,[collection]);ety=Some Int;espan=s}
       ) else if name="prepend" then (
         check_arity 2;
         let collection,element=list_argument (List.hd args) in
         let value=check_expr env scope (Some element) (List.nth args 1) in
         {node=XCall(None,name,[collection;value]);ety=Some(List element);espan=s}
       ) else if name="reverse" then (
         check_arity 1;
         let collection,element=list_argument (List.hd args) in
         {node=XCall(None,name,[collection]);ety=Some(List element);espan=s}
       ) else if name="byte_length" then (
         check_arity 1;
         let source=check_expr env scope (Some Str) (List.hd args) in
         {node=XCall(None,name,[source]);ety=Some Int;espan=s}
       ) else if name="byte_at" then (
         check_arity 2;
         let source=check_expr env scope (Some Str) (List.hd args) in
         let offset=check_expr env scope (Some Int) (List.nth args 1) in
         {node=XCall(None,name,[source;offset]);ety=Some Int;espan=s}
       ) else if name="byte_slice" then (
         check_arity 3;
         let source=check_expr env scope (Some Str) (List.hd args) in
         let start=check_expr env scope (Some Int) (List.nth args 1) in
         let finish=check_expr env scope (Some Int) (List.nth args 2) in
         {node=XCall(None,name,[source;start;finish]);ety=Some Str;espan=s}
       ) else if name="append" then (
         check_arity 2;
         let collection,element=list_argument (List.nth args 0) in
         let value=check_expr env scope (Some element) (List.nth args 1) in
         {node=XCall(None,name,[collection;value]);ety=Some(List element);espan=s}
       ) else if name="contains" then (
         check_arity 2;
         let collection,element=list_argument (List.hd args) in
         if not(scalar_equality_type element) then fail "PEP_MEMBERSHIP_UNSUPPORTED" ("Membership is not defined for "^type_name element) (expr_span (List.hd args)) ();
         let value=check_expr env scope (Some element) (List.nth args 1) in
         {node=XCall(None,name,[collection;value]);ety=Some Bool;espan=s}
       ) else (
         let params,result,fid = if name="semantic_snapshot" then [],Named "ProgramInfo",None else if name="source_bytes" then [],Str,None else if name="say" then [Str],Unit,None else if name="int_text" then [Int],Str,None else
           match Hashtbl.find_opt signatures name with None->
             let constructor_like=name<>"" && name.[0]>='A' && name.[0]<='Z' in
             let code=if constructor_like then "PEP_UNKNOWN_CONSTRUCTOR" else "PEP_UNKNOWN_FUNCTION" in
             fail code ((if constructor_like then "Unknown constructor '" else "Unknown function '")^name^"'") s ()
            |Some f->List.map snd f.params,f.result,Some f.fid in
         if List.length args<>List.length params then fail "PEP_ARGUMENT_COUNT" (Printf.sprintf "Function '%s' expects %d argument(s), found %d" name (List.length params) (List.length args)) s ();
         let checked=List.map2(fun arg ty->check_expr env scope (Some ty) arg)args params in
         {node=XCall(fid,name,checked);ety=Some result;espan=s}
       )
  and match_expr env scope expected subject arms sp =
    if arms=[] then fail "PEP_EMPTY_MATCH" "A match expression must have at least one arm" sp ();
    let checked_subject=synth env scope subject in
    let union=match checked_subject.ety with Some(Named name)->(match Hashtbl.find_opt type_table name with Some (`Union info)->info|_->fail "PEP_MATCH_NON_UNION" ("Match subject type '"^name^"' is not a tagged union") (expr_span subject) ())|Some ty->fail "PEP_MATCH_NON_UNION" ("Match subject type '"^type_name ty^"' is not a tagged union") (expr_span subject) ()|None->fail "PEP_MATCH_UNTYPED" "Match subject has no known type" (expr_span subject) () in
    let catch_all=ref false and covered=Hashtbl.create 8 and seen=Hashtbl.create 8 in
    let arm_contexts=List.map(fun (arm:match_arm)->
      if !catch_all then fail "PEP_UNREACHABLE_MATCH_ARM" "Match arm follows an irrefutable pattern" arm.arm_span ();
      let local=ref [] in
      let pattern,_=check_pattern local (Named union.union_name) arm.pattern in
      let rec pattern_key = function PWildcard _|PBind _->"_"|PConstructor(n,args,_)->n^"("^String.concat "," (List.map pattern_key args)^")" in
      let key=pattern_key arm.pattern in
      if Hashtbl.mem seen key then fail "PEP_DUPLICATE_MATCH_ARM" "Duplicate or unreachable match arm" arm.arm_span ();
      Hashtbl.add seen key ();
      (match arm.pattern with
       |PWildcard _|PBind _ ->catch_all:=true
       |PConstructor(name,args,_) ->let cid,_,arg_types,_=match Hashtbl.find constructor_table name with _,item->item in
          if Hashtbl.mem covered cid then fail "PEP_UNREACHABLE_MATCH_ARM" ("Constructor '"^name^"' is already covered") arm.arm_span ();
          if List.length args=List.length arg_types && List.for_all2 pattern_covers arg_types args then Hashtbl.replace covered cid ());
      let arm_env=(if !local=[] then env else !local::env) in
      pattern,arm_env,arm
    )arms in
    if not !catch_all then List.iter(fun(cid,name,_,_)->if not(Hashtbl.mem covered cid) then fail "PEP_NON_EXHAUSTIVE_MATCH" ("Match is missing an irrefutable arm for constructor '"^name^"'") sp ()) union.union_variants;
    let inferred_type=match expected with Some _ as ty->ty |None->
      let rec find : (tpattern * binding list list * match_arm) list -> ty option = function
        |[]->None
        |(_,arm_env,(arm:match_arm))::rest->
            let saved_holes= !holes in holes:=[];
            let inferred=try (synth arm_env scope arm.result).ety with Error _->None in
            holes:=saved_holes;
            (match inferred with Some _->inferred|None->find rest)
      in find arm_contexts in
    let checked_arms=List.map(fun(pattern,arm_env,(arm:match_arm))->
      let result=try check_expr arm_env scope inferred_type arm.result with Error diagnostic when diagnostic.code="PEP_TYPE_MISMATCH" -> fail "PEP_MATCH_ARM_TYPE_MISMATCH" diagnostic.message diagnostic.at ?expected:diagnostic.expected () in
      pattern,result)arm_contexts in
    let result_type=match inferred_type with Some _->inferred_type|None->
      match List.find_opt(fun(_,result)->result.ety<>None)checked_arms with None->None|Some(_,result)->result.ety in
    {node=XMatch(checked_subject,List.map(fun(p,r)->{tpattern=p;tresult=r})checked_arms);ety=result_type;espan=sp}
  in
  let rec check_stmts env scope expected xs =
    let rec loop env acc terminated = function
     |[]->List.rev acc,env,terminated
     |s::rest when terminated->fail "PEP_UNREACHABLE" "Statement follows an unconditional return" (stmt_span s) ()
     |SLet(name,annotation,e,sp)::rest ->
       if has_current env name then fail "PEP_DUPLICATE_BINDING" ("Duplicate binding '"^name^"' in this scope") sp ();
       (match annotation with Some ty->valid_type ty sp|None->());
       let te=match annotation with Some t->check_expr env scope (Some t) e|None->synth env scope e in
       let ty=match annotation,te.ety with Some t,_->Some t|None,t->t in
       let b={bid=fresh();bname=name;bty=ty;bspan=sp;mutable_=false} in
       let env'=(match env with []->[[b]]|h::tl->(b::h)::tl) in
       loop env' (TLet(b,te)::acc) false rest
     |SVar(name,annotation,e,sp)::rest ->
       if has_current env name then fail "PEP_DUPLICATE_BINDING" ("Duplicate binding '"^name^"' in this scope") sp ();
       (match annotation with Some ty->valid_type ty sp|None->());
       let te=match annotation with Some t->check_expr env scope (Some t) e|None->synth env scope e in
       let ty=match annotation,te.ety with Some t,_->Some t|None,t->t in
       let b={bid=fresh();bname=name;bty=ty;bspan=sp;mutable_=true} in
       let env'=(match env with []->[[b]]|h::tl->(b::h)::tl) in
       loop env' (TVar(b,te)::acc) false rest
     |SAssign(name,e,sp)::rest->
       let binding=match lookup env name with
         |None->fail "PEP_UNKNOWN_VARIABLE" ("Unknown variable '"^name^"'") sp ()
         |Some binding when not binding.mutable_->fail "PEP_ASSIGN_IMMUTABLE" ("Cannot assign to immutable binding '"^name^"'") sp ()
         |Some binding->binding in
       let expected_type=match binding.bty with Some ty->Some ty|None->fail "PEP_UNCONSTRAINED_BINDING" ("Cannot assign to binding '"^name^"' without a known type") sp () in
       let value=check_expr env scope expected_type e in
       loop env (TAssign(binding,value,sp)::acc) false rest
     |SReturn(e,sp)::rest ->
       if expected=None then fail "PEP_RETURN_OUTSIDE_FUNCTION" "return is only valid inside a function" sp ();
       let te=check_expr env scope expected e in loop env (TReturn te::acc) true rest
     |SExpr(e,_)::rest->let te=synth env scope e in loop env (TExpr te::acc) false rest
     |SBlock(body,_)::rest->let inner,_,term=check_stmts ([]::env) scope expected body in loop env (TBlock inner::acc) term rest
     |SIf(condition,yes,no,sp)::rest->
       let checked_condition=check_expr env scope (Some Bool) condition in
       let checked_yes,_,yes_returns=check_stmts ([]::env) scope expected yes in
       let checked_no,_,no_returns=check_stmts ([]::env) scope expected no in
       loop env (TIf(checked_condition,checked_yes,checked_no,sp)::acc) (yes_returns && no_returns) rest
     |SFor(name,values,body,sp)::rest->
       let checked_values=synth env scope values in
       let element_type=match checked_values.ety with Some(List ty)->ty|Some ty->fail "PEP_FOR_REQUIRES_LIST" ("for-in requires a List, found "^type_name ty) (expr_span values) ()|None->fail "PEP_FOR_REQUIRES_LIST" "for-in requires a list with a known element type" (expr_span values) () in
       let binding={bid=fresh();bname=name;bty=Some element_type;bspan=sp;mutable_=false} in
       let inner,_,_=check_stmts ([binding]::env) scope expected body in
       loop env (TFor(binding,checked_values,inner,sp)::acc) false rest
     |SWhile(condition,body,sp)::rest->
       let checked_condition=check_expr env scope (Some Bool) condition in
       let inner,_,_=check_stmts ([]::env) scope expected body in
       loop env (TWhile(checked_condition,inner,sp)::acc) false rest
    in loop env [] false xs
  in
  let functions=ref [] in
  List.iter(function TopFun f->
    let sig_=Hashtbl.find signatures f.fname in
    let seen=Hashtbl.create 8 in
    let params=List.map(fun(n,t,s)->if Hashtbl.mem seen n then fail "PEP_DUPLICATE_PARAMETER" ("Duplicate parameter '"^n^"'") s ();Hashtbl.add seen n ();{bid=fresh();bname=n;bty=Some t;bspan=s;mutable_=false})f.params in
    let typed,_,terminated=check_stmts [params] f.fname (Some f.result) f.body in
    if f.result<>Unit && not terminated then fail "PEP_MISSING_RETURN" ("Function '"^f.fname^"' must return "^type_name f.result) f.fspan ~expected:f.result ();
    functions:={sig_;tparams=params;tbody=typed}::!functions
   |_->()) tops;
  let global_env=ref [[]] and top_typed=ref [] in
  List.iter(function TopStmt s->let typed,env,_=check_stmts !global_env "<top-level>" None [s] in global_env:=env;top_typed:=List.rev_append typed !top_typed|_->())tops;
  {functions=List.rev !functions;tops=List.rev !top_typed;holes=List.rev !holes;records=List.rev !records;unions=List.rev !unions}

let rec typed_expr_json e =
 let typ=match e.ety with None->"null"|Some t->json_string(type_name t) in
 let node=match e.node with
 |XInt n->"{\"kind\":\"int\",\"value\":"^Int64.to_string n^"}"
 |XBool b->"{\"kind\":\"bool\",\"value\":"^string_of_bool b^"}"
 |XStr s->"{\"kind\":\"string\",\"value\":"^json_string s^"}"
 |XVar id->"{\"kind\":\"binding\",\"bindingId\":"^string_of_int id^"}"
 |XHole h->"{\"kind\":\"hole\",\"name\":"^(match h with None->"null"|Some x->json_string x)^"}"
 |XCall(fid,n,args)->"{\"kind\":\"call\",\"name\":"^json_string n^",\"functionId\":"^(match fid with None->"null"|Some x->string_of_int x)^",\"arguments\":["^String.concat ","(List.map typed_expr_json args)^"]}"
 |XBin(op,a,b)->"{\"kind\":\"binary\",\"operator\":"^json_string op^",\"left\":"^typed_expr_json a^",\"right\":"^typed_expr_json b^"}"
 |XUnary(op,value)->"{\"kind\":\"unary\",\"operator\":"^json_string op^",\"value\":"^typed_expr_json value^"}"
 |XList(items)->"{\"kind\":\"list\",\"elements\":["^String.concat ","(List.map typed_expr_json items)^"]}"
 |XIf(c,y,n)->"{\"kind\":\"if\",\"condition\":"^typed_expr_json c^",\"then\":"^typed_expr_json y^",\"else\":"^typed_expr_json n^"}"
 |XRecord(id,fields)->"{\"kind\":\"record\",\"typeId\":"^string_of_int id^",\"fields\":["^String.concat "," (List.map(fun(fid,value)->"{\"fieldId\":"^string_of_int fid^",\"value\":"^typed_expr_json value^"}")fields)^"]}"
 |XField(id,value)->"{\"kind\":\"field_access\",\"fieldId\":"^string_of_int id^",\"value\":"^typed_expr_json value^"}"
 |XConstructor(type_id,ctor_id,name,args)->"{\"kind\":\"constructor\",\"typeId\":"^string_of_int type_id^",\"constructorId\":"^string_of_int ctor_id^",\"name\":"^json_string name^",\"arguments\":["^String.concat "," (List.map typed_expr_json args)^"]}"
 |XMatch(subject,arms)->"{\"kind\":\"match\",\"value\":"^typed_expr_json subject^",\"arms\":["^String.concat "," (List.map(fun arm->"{\"pattern\":"^typed_pattern_json arm.tpattern^",\"result\":"^typed_expr_json arm.tresult^"}")arms)^"]}" in
 "{\"type\":"^typ^",\"span\":"^span_json e.espan^",\"expression\":"^node^"}"
and typed_pattern_json = function
 |TPWildcard sp->"{\"kind\":\"wildcard\",\"span\":"^span_json sp^"}"
 |TPBind binding->"{\"kind\":\"binding\",\"name\":"^json_string binding.bname^",\"bindingId\":"^string_of_int binding.bid^",\"mutable\":false,\"span\":"^span_json binding.bspan^"}"
 |TPConstructor(id,arguments,sp)->"{\"kind\":\"constructor\",\"constructorId\":"^string_of_int id^",\"arguments\":["^String.concat "," (List.map typed_pattern_json arguments)^"],\"span\":"^span_json sp^"}"
let rec typed_stmt_json = function
 |TLet(b,e)->"{\"kind\":\"let\",\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^",\"type\":"^(match b.bty with None->"null"|Some t->json_string(type_name t))^",\"mutable\":false,\"value\":"^typed_expr_json e^"}"
 |TVar(b,e)->"{\"kind\":\"var\",\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^",\"type\":"^(match b.bty with None->"null"|Some t->json_string(type_name t))^",\"mutable\":true,\"value\":"^typed_expr_json e^"}"
 |TAssign(b,e,sp)->"{\"kind\":\"assignment\",\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^",\"span\":"^span_json sp^",\"value\":"^typed_expr_json e^"}"
 |TReturn e->"{\"kind\":\"return\",\"value\":"^typed_expr_json e^"}"
 |TBlock xs->"{\"kind\":\"block\",\"statements\":["^String.concat ","(List.map typed_stmt_json xs)^"]}"
 |TIf(c,y,n,sp)->"{\"kind\":\"if_statement\",\"condition\":"^typed_expr_json c^",\"then\":["^String.concat ","(List.map typed_stmt_json y)^"],\"else\":["^String.concat ","(List.map typed_stmt_json n)^"],\"span\":"^span_json sp^"}"
 |TFor(b,values,body,sp)->"{\"kind\":\"for_in\",\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^",\"type\":"^json_string(type_name(Option.get b.bty))^",\"iterable\":"^typed_expr_json values^",\"body\":["^String.concat ","(List.map typed_stmt_json body)^"],\"span\":"^span_json sp^"}"
 |TWhile(c,body,sp)->"{\"kind\":\"while\",\"condition\":"^typed_expr_json c^",\"body\":["^String.concat ","(List.map typed_stmt_json body)^"],\"span\":"^span_json sp^"}"
 |TExpr e->"{\"kind\":\"expression\",\"value\":"^typed_expr_json e^"}"
let typed_json_base c =
 "{\"functions\":["^String.concat ","(List.map(fun f->"{\"functionId\":"^string_of_int f.sig_.fid^",\"name\":"^json_string f.sig_.name^",\"parameters\":["^String.concat ","(List.map(fun b->"{\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^",\"type\":"^json_string(type_name(Option.get b.bty))^"}")f.tparams)^"],\"returnType\":"^json_string(type_name f.sig_.result)^",\"body\":["^String.concat ","(List.map typed_stmt_json f.tbody)^"]}")c.functions)^"],\"statements\":["^String.concat ","(List.map typed_stmt_json c.tops)^"]}"
let typed_json c =
 let record_json r = "{\"kind\":\"record\",\"typeId\":"^string_of_int r.record_id^",\"name\":"^json_string r.record_name^",\"fields\":["^String.concat "," (List.map(fun(id,name,ty,sp)->"{\"fieldId\":"^string_of_int id^",\"name\":"^json_string name^",\"type\":"^json_string(type_name ty)^",\"span\":"^span_json sp^"}")r.record_fields)^"]}" in
 let union_json u = "{\"kind\":\"union\",\"typeId\":"^string_of_int u.union_id^",\"name\":"^json_string u.union_name^",\"variants\":["^String.concat "," (List.map(fun(id,name,args,sp)->"{\"constructorId\":"^string_of_int id^",\"name\":"^json_string name^",\"arguments\":["^String.concat "," (List.map(fun ty->json_string(type_name ty))args)^"],\"span\":"^span_json sp^"}")u.union_variants)^"]}" in
 let declarations=String.concat "," (List.map record_json c.records @ List.map union_json c.unions) in
 let base=typed_json_base c in
 "{\"types\":["^declarations^"],"^String.sub base 1 (String.length base-1)
let hole_json h =
 let bindings="["^String.concat ","(List.map(fun b->"{\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^",\"type\":"^(match b.bty with None->"null"|Some t->json_string(type_name t))^",\"mutable\":"^string_of_bool b.mutable_^"}")h.hbindings)^"]" in
 let actions=match h.hty with None->"[]"|Some ty->"[{\"kind\":\"fill_hole\",\"expectedType\":"^json_string(type_name ty)^",\"candidates\":["^String.concat ","(List.map(fun b->"{\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^"}")(candidates ty h.hbindings))^"]}]" in
 "{\"identity\":"^(match h.hid with None->"null"|Some x->json_string x)^",\"scope\":"^json_string h.hscope^",\"expectedType\":"^(match h.hty with None->"null"|Some t->json_string(type_name t))^",\"bindings\":"^bindings^",\"actions\":"^actions^",\"span\":"^span_json h.hspan^"}"
let diag_json d = "{\"schemaVersion\":2,\"status\":\"invalid\",\"diagnostics\":[{\"code\":"^json_string d.code^",\"severity\":\"error\",\"message\":"^json_string d.message^",\"expectedType\":"^(match d.expected with None->"null"|Some t->json_string(type_name t))^",\"span\":"^span_json d.at^"}]}"
let program_status c = if c.holes=[] then "valid" else "incomplete"
let check_json tops c = "{\"schemaVersion\":2,\"status\":"^json_string(program_status c)^",\"ast\":"^ast_json tops^",\"typedTree\":"^typed_json c^",\"holes\":["^String.concat ","(List.map hole_json c.holes)^"],\"diagnostics\":[]}"

type value = VInt of int64|VBool of bool|VStr of string|VUnit|VRecord of int*(int*value) list|VVariant of int*int*value list|VList of value list
exception Runtime of string*string*span
let runtime code message sp=raise(Runtime(code,message,sp))
let int_value = function VInt n->n|_->assert false
let scalar_equal left right = match left,right with
 |VInt a,VInt b->a=b|VBool a,VBool b->a=b|VStr a,VStr b->String.equal a b|VUnit,VUnit->true|_->false
let checked_bin op a b sp =
 let add_over x y = y>0L && x>Int64.sub Int64.max_int y || y<0L && x<Int64.sub Int64.min_int y in
 let sub_over x y = y<0L && x>Int64.add Int64.max_int y || y>0L && x<Int64.add Int64.min_int y in
 let mul_over x y = if x=0L||y=0L then false else if x=Int64.min_int then y= -1L else if y=Int64.min_int then x= -1L else if x>0L then (if y>0L then x>Int64.div Int64.max_int y else y<Int64.div Int64.min_int x) else (if y>0L then x<Int64.div Int64.min_int y else y<Int64.div Int64.max_int x) in
 match op with
 |"<="->VBool(a<=b)
 |"+"->if add_over a b then runtime "PEP_RUNTIME_OVERFLOW" "Integer addition overflow" sp else VInt(Int64.add a b)
 |"-"->if sub_over a b then runtime "PEP_RUNTIME_OVERFLOW" "Integer subtraction overflow" sp else VInt(Int64.sub a b)
 |"*"->if mul_over a b then runtime "PEP_RUNTIME_OVERFLOW" "Integer multiplication overflow" sp else VInt(Int64.mul a b)
 |"/"->if b=0L then runtime "PEP_RUNTIME_DIVISION_BY_ZERO" "Division by zero" sp else if a=Int64.min_int&&b= -1L then runtime "PEP_RUNTIME_OVERFLOW" "Integer division overflow" sp else VInt(Int64.div a b)
 |"neg"->if b=Int64.min_int then runtime "PEP_RUNTIME_OVERFLOW" "Integer negation overflow" sp else VInt(Int64.neg b)
 |_ ->assert false
let execute ?(entry=None) ?(allow_say=true) ?(step_limit=1_000_000) ?(max_depth=512) ?(semantic_snapshot_value=None) ?(source_bytes_value=None) c =
 let fs=Hashtbl.create 16 in List.iter(fun f->Hashtbl.add fs f.sig_.fid f)c.functions;
 let remaining_steps = ref step_limit in
 let tick sp =
   decr remaining_steps;
   if !remaining_steps < 0 then runtime "PEP_RUNTIME_STEP_LIMIT" "Execution step budget exceeded" sp
 in
 let rec eval env callstack e =
  tick e.espan;
  match e.node with
  |XInt n->VInt n|XBool b->VBool b|XStr s->VStr s
  |XVar id->(try !(List.assoc id env) with Not_found->runtime "PEP_RUNTIME_UNRESOLVED_BINDING" "Checked binding is missing at runtime" e.espan)
  |XHole _->runtime "PEP_RUNTIME_HOLE" "Cannot execute an incomplete expression" e.espan
  |XList items->
    let rec collect acc=function []->VList(List.rev acc)|item::rest->let value=eval env callstack item in tick e.espan;collect(value::acc)rest in collect [] items
  |XUnary("!",value)->(match eval env callstack value with VBool result->VBool(not result)|_->runtime "PEP_RUNTIME_EXPECTED_BOOL" "Checked logical negation received a non-Bool value" e.espan)
  |XUnary(operator,_)->runtime "PEP_RUNTIME_UNKNOWN_UNARY_OPERATOR" ("Unsupported checked unary operator '"^operator^"'") e.espan
  |XRecord(id,fields)->VRecord(id,List.map(fun(fid,value)->fid,eval env callstack value)fields)
  |XField(fid,value)->(match eval env callstack value with VRecord(_,fields)->(try List.assoc fid fields with Not_found->runtime "PEP_RUNTIME_MISSING_FIELD" "Checked record field is missing at runtime" e.espan)|_->runtime "PEP_RUNTIME_EXPECTED_RECORD" "Checked field access received a non-record value" e.espan)
  |XConstructor(type_id,ctor_id,_,args)->VVariant(type_id,ctor_id,List.map(eval env callstack)args)
  |XMatch(subject,arms)->
    let value=eval env callstack subject in
    let rec select=function
      |[]->runtime "PEP_RUNTIME_NONEXHAUSTIVE_MATCH" "No checked match arm accepted the value" e.espan
      |arm::rest->(match match_pattern [] arm.tpattern value with Some arm_env->eval (arm_env@env) callstack arm.tresult|None->select rest)
    in select arms
  |XBin("&&",left,right)->(match eval env callstack left with VBool false->VBool false|VBool true->(match eval env callstack right with VBool result->VBool result|_->runtime "PEP_RUNTIME_EXPECTED_BOOL" "Checked logical conjunction received a non-Bool value" e.espan)|_->runtime "PEP_RUNTIME_EXPECTED_BOOL" "Checked logical conjunction received a non-Bool value" e.espan)
  |XBin("||",left,right)->(match eval env callstack left with VBool true->VBool true|VBool false->(match eval env callstack right with VBool result->VBool result|_->runtime "PEP_RUNTIME_EXPECTED_BOOL" "Checked logical disjunction received a non-Bool value" e.espan)|_->runtime "PEP_RUNTIME_EXPECTED_BOOL" "Checked logical disjunction received a non-Bool value" e.espan)
  |XBin(("=="|"!=") as op,left,right)->
    let left_value=eval env callstack left in let right_value=eval env callstack right in
    let equal=scalar_equal left_value right_value in VBool(if op="==" then equal else not equal)
  |XBin(op,a,b)->let left=eval env callstack a in let right=eval env callstack b in checked_bin op (int_value left) (int_value right) e.espan
  |XIf(c,y,n)->(match eval env callstack c with VBool true->eval env callstack y|VBool false->eval env callstack n|_->assert false)
  |XCall(fid,name,args)->
    let values=List.fold_left(fun acc arg->let value=eval env callstack arg in value::acc)[]args |> List.rev in
    if name="length" then (match values with
      |[VList items]->let rec count total=function []->VInt(Int64.of_int total)|_::rest->tick e.espan;count (total+1) rest in count 0 items
      |_ ->runtime "PEP_RUNTIME_EXPECTED_LIST" "Checked length received a non-list value" e.espan)
    else if name="prepend" then (match values with
      |[VList items;value]->tick e.espan;VList(value::items)
      |_ ->runtime "PEP_RUNTIME_EXPECTED_LIST" "Checked prepend received invalid arguments" e.espan)
    else if name="reverse" then (match values with
      |[VList items]->
        let rec copy result=function []->VList result|head::rest->tick e.espan;copy (head::result) rest in copy [] items
      |_ ->runtime "PEP_RUNTIME_EXPECTED_LIST" "Checked reverse received invalid arguments" e.espan)
    else if name="byte_length" then (match values with
      |[VStr source]->VInt(Int64.of_int(String.length source))
      |_ ->runtime "PEP_RUNTIME_BUILTIN" "Checked byte_length received invalid arguments" e.espan)
    else if name="byte_at" then (match values with
      |[VStr source;VInt offset] when offset>=0L && offset<Int64.of_int(String.length source)->VInt(Int64.of_int(Char.code source.[Int64.to_int offset]))
      |[VStr _;VInt _]->runtime "PEP_RUNTIME_BYTE_RANGE" "Byte offset is outside the source" e.espan
      |_ ->runtime "PEP_RUNTIME_BUILTIN" "Checked byte_at received invalid arguments" e.espan)
    else if name="byte_slice" then (match values with
      |[VStr source;VInt start;VInt finish]->
        let length=Int64.of_int(String.length source) in
        if start<0L || finish<start || finish>length then runtime "PEP_RUNTIME_BYTE_RANGE" "Byte slice must be a valid half-open source range" e.espan;
        let boundary offset=offset=0L || offset=length || Char.code source.[Int64.to_int offset] land 0xc0 <> 0x80 in
        if not(boundary start && boundary finish) then runtime "PEP_RUNTIME_BYTE_BOUNDARY" "Byte slice boundary splits a UTF-8 sequence" e.espan;
        let first=Int64.to_int start and count=Int64.to_int(Int64.sub finish start) in
        for _=1 to count do tick e.espan done;
        VStr(String.sub source first count)
      |_ ->runtime "PEP_RUNTIME_BUILTIN" "Checked byte_slice received invalid arguments" e.espan)
    else if name="source_bytes" then (match source_bytes_value with
      |Some source->source
      |None->runtime "PEP_RUNTIME_SOURCE_CONTEXT" "source_bytes is available only for a host-authorised v2 semanticTarget" e.espan)
    else if name="append" then (match values with
      |[VList items;value]->
        let rec copy reversed=function
          |[]->tick e.espan;let tail=[value] in
            let rec restore remaining result=match remaining with
              |[]->VList result
              |head::rest->tick e.espan;restore rest (head::result)
            in restore reversed tail
          |head::rest->tick e.espan;copy (head::reversed) rest
        in copy [] items
      |_ ->runtime "PEP_RUNTIME_EXPECTED_LIST" "Checked append received invalid arguments" e.espan)
    else if name="contains" then (match values with
      |[VList items;value]->
        let rec find=function []->false|head::rest->tick e.espan;if scalar_equal head value then true else find rest in VBool(find items)
      |_ ->runtime "PEP_RUNTIME_EXPECTED_LIST" "Checked contains received invalid arguments" e.espan)
    else if name="semantic_snapshot" then (match semantic_snapshot_value with Some value->value|None->runtime "PEP_RUNTIME_SEMANTIC_CONTEXT" "semantic_snapshot is available only during a host-authorised tool invocation" e.espan)
    else if name="say" then (if not allow_say then runtime "PEP_RUNTIME_TOOL_EFFECT" "say is unavailable during tool execution" e.espan else match values with [VStr text]->print_endline text;VUnit|_->runtime "PEP_RUNTIME_BUILTIN" "Checked say received invalid arguments" e.espan)
    else if name="int_text" then (match values with [VInt number]->VStr(Int64.to_string number)|_->runtime "PEP_RUNTIME_BUILTIN" "Checked int_text received invalid arguments" e.espan)
    else match fid with
      |None->runtime "PEP_RUNTIME_UNKNOWN_CALL" ("Unknown checked call '"^name^"'") e.espan
      |Some id->
        if List.length callstack>=max_depth then runtime "PEP_RUNTIME_CALL_DEPTH" "Maximum function call depth exceeded" e.espan;
        let function_=Hashtbl.find fs id in
        let env'=List.map2(fun binding value->binding.bid,ref value)function_.tparams values in
        (match exec_stmts env' (name::callstack) function_.tbody with Some value->value|None->VUnit)
 and match_pattern env pattern value = match pattern,value with
  |TPWildcard _,_->Some env
  |TPBind binding,value->Some((binding.bid,ref value)::env)
  |TPConstructor(cid,patterns,_),VVariant(_,actual,args) when cid=actual && List.length patterns=List.length args->
    List.fold_left2(fun result pattern value->match result with None->None|Some env->match_pattern env pattern value)(Some env)patterns args
  |TPConstructor _,_->None
 and exec_stmts env stack = function
  |[]->None
  |stmt::rest->
    let statement_span=match stmt with
      |TLet(binding,_)|TVar(binding,_)->binding.bspan
      |TAssign(_,_,span)|TIf(_,_,_,span)|TFor(_,_,_,span)|TWhile(_,_,span)->span
      |TReturn expression|TExpr expression->expression.espan
      |TBlock _->mkspan 0 0 1 1 in
    tick statement_span;
    (match stmt with
     |TLet(binding,expression)|TVar(binding,expression)->
       let value=eval env stack expression in
       exec_stmts ((binding.bid,ref value)::env) stack rest
     |TAssign(binding,expression,span)->
       let value=eval env stack expression in
       (try (List.assoc binding.bid env):=value with Not_found->runtime "PEP_RUNTIME_UNRESOLVED_BINDING" "Checked assignment target is missing at runtime" span);
       exec_stmts env stack rest
     |TReturn expression->Some(eval env stack expression)
     |TBlock statements->(match exec_stmts env stack statements with Some value->Some value|None->exec_stmts env stack rest)
     |TIf(condition,yes,no,span)->
       (match eval env stack condition with
        |VBool true->(match exec_stmts env stack yes with Some value->Some value|None->exec_stmts env stack rest)
        |VBool false->(match exec_stmts env stack no with Some value->Some value|None->exec_stmts env stack rest)
        |_ ->runtime "PEP_RUNTIME_EXPECTED_BOOL" "Checked if condition received a non-Bool value" span)
     |TFor(binding,iterable,body,span)->
       (match eval env stack iterable with
        |VList values->
          let rec iterate=function
            |[]->exec_stmts env stack rest
            |value::remaining->
              tick span;
              (match exec_stmts ((binding.bid,ref value)::env) stack body with
               |Some result->Some result
               |None->iterate remaining)
          in iterate values
        |_ ->runtime "PEP_RUNTIME_EXPECTED_LIST" "Checked for-in received a non-list value" span)
     |TWhile(condition,body,span)->
       let rec repeat () =
         match eval env stack condition with
         |VBool false->exec_stmts env stack rest
         |VBool true->tick span;(match exec_stmts env stack body with Some result->Some result|None->repeat())
         |_ ->runtime "PEP_RUNTIME_EXPECTED_BOOL" "Checked while condition received a non-Bool value" span
       in repeat()
     |TExpr expression->ignore(eval env stack expression);exec_stmts env stack rest)
 in
 match entry with
 |None -> ignore(exec_stmts [] [] c.tops); VUnit
 |Some (function_id,arguments) ->
   let f = match List.find_opt (fun f -> f.sig_.fid=function_id) c.functions with
     |Some f -> f |None -> runtime "PEP_RUNTIME_UNKNOWN_FUNCTION" "Checked tool function is missing" (mkspan 0 0 1 1) in
   if List.length arguments <> List.length f.tparams then runtime "PEP_RUNTIME_ARGUMENT_COUNT" "Tool argument count did not match the checked function" f.sig_.decl.fspan;
   let env = List.map2 (fun binding value -> binding.bid,ref value) f.tparams arguments in
   match exec_stmts env [f.sig_.name] f.tbody with Some value -> value |None -> VUnit

(* Session protocol v3. Revisions are content-addressed and each analysis is
   immutable; only a document's current-revision pointer changes. *)
type json_value =
  | JObject of (string * json_value) list
  | JArray of json_value list
  | JString of string
  | JNumber of string
  | JBool of bool
  | JNull

exception Json_parse_error of string
exception Session_error of string * string
exception Session_document_error of string * string * string * string

let json_fail message = raise (Json_parse_error message)

let valid_utf8 text = invalid_utf8_offset text = None

let add_utf8 buffer codepoint =
  if codepoint < 0 || codepoint > 0x10ffff || codepoint >= 0xd800 && codepoint <= 0xdfff then
    json_fail "Invalid Unicode scalar value";
  if codepoint <= 0x7f then Buffer.add_char buffer (Char.chr codepoint)
  else if codepoint <= 0x7ff then (
    Buffer.add_char buffer (Char.chr (0xc0 lor (codepoint lsr 6)));
    Buffer.add_char buffer (Char.chr (0x80 lor (codepoint land 0x3f)))
  ) else if codepoint <= 0xffff then (
    Buffer.add_char buffer (Char.chr (0xe0 lor (codepoint lsr 12)));
    Buffer.add_char buffer (Char.chr (0x80 lor ((codepoint lsr 6) land 0x3f)));
    Buffer.add_char buffer (Char.chr (0x80 lor (codepoint land 0x3f)))
  ) else (
    Buffer.add_char buffer (Char.chr (0xf0 lor (codepoint lsr 18)));
    Buffer.add_char buffer (Char.chr (0x80 lor ((codepoint lsr 12) land 0x3f)));
    Buffer.add_char buffer (Char.chr (0x80 lor ((codepoint lsr 6) land 0x3f)));
    Buffer.add_char buffer (Char.chr (0x80 lor (codepoint land 0x3f)))
  )

let parse_json input =
  if not (valid_utf8 input) then json_fail "JSON input is not valid UTF-8";
  let length = String.length input and cursor = ref 0 in
  let fail message = json_fail (Printf.sprintf "%s at byte %d" message !cursor) in
  let peek () = if !cursor < length then input.[!cursor] else '\000' in
  let take () = if !cursor >= length then fail "Unexpected end of JSON" else let c = input.[!cursor] in incr cursor; c in
  let rec whitespace () = match peek () with ' ' | '\t' | '\r' | '\n' -> incr cursor; whitespace () | _ -> () in
  let expect c = if take () <> c then fail (Printf.sprintf "Expected %C" c) in
  let hex_value = function
    | '0'..'9' as c -> Char.code c - Char.code '0'
    | 'a'..'f' as c -> Char.code c - Char.code 'a' + 10
    | 'A'..'F' as c -> Char.code c - Char.code 'A' + 10
    | _ -> fail "Invalid hexadecimal escape"
  in
  let hex4 () =
    let value = ref 0 in
    for _ = 1 to 4 do value := (!value lsl 4) lor hex_value (take ()) done;
    !value
  in
  let parse_string () =
    expect '"';
    let buffer = Buffer.create 32 in
    let rec loop () = match take () with
      | '"' -> Buffer.contents buffer
      | '\\' ->
          (match take () with
           | '"' -> Buffer.add_char buffer '"'
           | '\\' -> Buffer.add_char buffer '\\'
           | '/' -> Buffer.add_char buffer '/'
           | 'b' -> Buffer.add_char buffer '\b'
           | 'f' -> Buffer.add_char buffer '\012'
           | 'n' -> Buffer.add_char buffer '\n'
           | 'r' -> Buffer.add_char buffer '\r'
           | 't' -> Buffer.add_char buffer '\t'
           | 'u' ->
               let first = hex4 () in
               let codepoint =
                 if first >= 0xd800 && first <= 0xdbff then (
                   if take () <> '\\' || take () <> 'u' then fail "Missing low surrogate";
                   let second = hex4 () in
                   if second < 0xdc00 || second > 0xdfff then fail "Invalid low surrogate";
                   0x10000 + ((first - 0xd800) lsl 10) + (second - 0xdc00)
                 ) else if first >= 0xdc00 && first <= 0xdfff then fail "Unexpected low surrogate"
                 else first
               in
               add_utf8 buffer codepoint
           | _ -> fail "Invalid JSON escape");
          loop ()
      | c when Char.code c < 0x20 -> fail "Unescaped control character in JSON string"
      | c -> Buffer.add_char buffer c; loop ()
    in
    loop ()
  in
  let parse_number () =
    let start = !cursor in
    ignore (if peek () = '-' then take () else '\000');
    (match peek () with
     | '0' -> ignore (take ()); if peek () >= '0' && peek () <= '9' then fail "Leading zero in JSON number"
     | '1'..'9' -> while peek () >= '0' && peek () <= '9' do ignore (take ()) done
     | _ -> fail "Invalid JSON number");
    if peek () = '.' then (
      ignore (take ());
      if not (peek () >= '0' && peek () <= '9') then fail "Invalid JSON fraction";
      while peek () >= '0' && peek () <= '9' do ignore (take ()) done
    );
    if peek () = 'e' || peek () = 'E' then (
      ignore (take ());
      if peek () = '+' || peek () = '-' then ignore (take ());
      if not (peek () >= '0' && peek () <= '9') then fail "Invalid JSON exponent";
      while peek () >= '0' && peek () <= '9' do ignore (take ()) done
    );
    JNumber (String.sub input start (!cursor - start))
  in
  let literal word value =
    for i = 0 to String.length word - 1 do if take () <> word.[i] then fail "Invalid JSON literal" done;
    value
  in
  let rec value () =
    whitespace ();
    match peek () with
    | '"' -> JString (parse_string ())
    | '{' -> object_value ()
    | '[' -> array_value ()
    | 't' -> literal "true" (JBool true)
    | 'f' -> literal "false" (JBool false)
    | 'n' -> literal "null" JNull
    | '-' | '0'..'9' -> parse_number ()
    | _ -> fail "Expected a JSON value"
  and object_value () =
    expect '{'; whitespace ();
    if peek () = '}' then (ignore (take ()); JObject [])
    else
      let fields = ref [] in
      let rec members () =
        whitespace ();
        if peek () <> '"' then fail "Expected a JSON object key";
        let key = parse_string () in
        if List.mem_assoc key !fields then fail "Duplicate JSON object key";
        whitespace (); expect ':';
        let field_value = value () in
        fields := (key, field_value) :: !fields;
        whitespace ();
        match take () with
        | '}' -> JObject (List.rev !fields)
        | ',' -> members ()
        | _ -> fail "Expected ',' or '}'"
      in members ()
  and array_value () =
    expect '['; whitespace ();
    if peek () = ']' then (ignore (take ()); JArray [])
    else
      let items = ref [] in
      let rec elements () =
        items := value () :: !items;
        whitespace ();
        match take () with
        | ']' -> JArray (List.rev !items)
        | ',' -> elements ()
        | _ -> fail "Expected ',' or ']'"
      in elements ()
  in
  let parsed = value () in
  whitespace ();
  if !cursor <> length then fail "Trailing data after JSON value";
  parsed

let sha256_constants = Array.map Int32.of_string [|
  "0x428a2f98"; "0x71374491"; "0xb5c0fbcf"; "0xe9b5dba5"; "0x3956c25b"; "0x59f111f1"; "0x923f82a4"; "0xab1c5ed5";
  "0xd807aa98"; "0x12835b01"; "0x243185be"; "0x550c7dc3"; "0x72be5d74"; "0x80deb1fe"; "0x9bdc06a7"; "0xc19bf174";
  "0xe49b69c1"; "0xefbe4786"; "0x0fc19dc6"; "0x240ca1cc"; "0x2de92c6f"; "0x4a7484aa"; "0x5cb0a9dc"; "0x76f988da";
  "0x983e5152"; "0xa831c66d"; "0xb00327c8"; "0xbf597fc7"; "0xc6e00bf3"; "0xd5a79147"; "0x06ca6351"; "0x14292967";
  "0x27b70a85"; "0x2e1b2138"; "0x4d2c6dfc"; "0x53380d13"; "0x650a7354"; "0x766a0abb"; "0x81c2c92e"; "0x92722c85";
  "0xa2bfe8a1"; "0xa81a664b"; "0xc24b8b70"; "0xc76c51a3"; "0xd192e819"; "0xd6990624"; "0xf40e3585"; "0x106aa070";
  "0x19a4c116"; "0x1e376c08"; "0x2748774c"; "0x34b0bcb5"; "0x391c0cb3"; "0x4ed8aa4a"; "0x5b9cca4f"; "0x682e6ff3";
  "0x748f82ee"; "0x78a5636f"; "0x84c87814"; "0x8cc70208"; "0x90befffa"; "0xa4506ceb"; "0xbef9a3f7"; "0xc67178f2"
|]

let sha256_hex text =
  let open Int32 in
  let rotr value count = logor (shift_right_logical value count) (shift_left value (32 - count)) in
  let xor3 a b c = logxor (logxor a b) c in
  let length = String.length text in
  let padded_length = ((length + 9 + 63) / 64) * 64 in
  let padded = Bytes.make padded_length '\000' in
  Bytes.blit_string text 0 padded 0 length;
  Bytes.set padded length '\128';
  let bit_length = Int64.mul (Int64.of_int length) 8L in
  for i = 0 to 7 do
    let shift = 8 * (7 - i) in
    let byte = Int64.to_int (Int64.logand (Int64.shift_right_logical bit_length shift) 0xffL) in
    Bytes.set padded (padded_length - 8 + i) (Char.chr byte)
  done;
  let state = Array.map of_string [|
    "0x6a09e667"; "0xbb67ae85"; "0x3c6ef372"; "0xa54ff53a";
    "0x510e527f"; "0x9b05688c"; "0x1f83d9ab"; "0x5be0cd19"
  |] in
  let words = Array.make 64 0l in
  for offset = 0 to (padded_length / 64) - 1 do
    let block = offset * 64 in
    for i = 0 to 15 do
      let at = block + i * 4 in
      let b0 = of_int (Char.code (Bytes.get padded at))
      and b1 = of_int (Char.code (Bytes.get padded (at + 1)))
      and b2 = of_int (Char.code (Bytes.get padded (at + 2)))
      and b3 = of_int (Char.code (Bytes.get padded (at + 3))) in
      words.(i) <- logor (shift_left b0 24) (logor (shift_left b1 16) (logor (shift_left b2 8) b3))
    done;
    for i = 16 to 63 do
      let x = words.(i - 15) and y = words.(i - 2) in
      let small0 = xor3 (rotr x 7) (rotr x 18) (shift_right_logical x 3)
      and small1 = xor3 (rotr y 17) (rotr y 19) (shift_right_logical y 10) in
      words.(i) <- add small1 (add words.(i - 7) (add small0 words.(i - 16)))
    done;
    let a = ref state.(0) and b = ref state.(1) and c = ref state.(2) and d = ref state.(3)
    and e = ref state.(4) and f = ref state.(5) and g = ref state.(6) and h = ref state.(7) in
    for i = 0 to 63 do
      let large1 = xor3 (rotr !e 6) (rotr !e 11) (rotr !e 25) in
      let choose = logxor (logand !e !f) (logand (lognot !e) !g) in
      let first = add !h (add large1 (add choose (add sha256_constants.(i) words.(i)))) in
      let large0 = xor3 (rotr !a 2) (rotr !a 13) (rotr !a 22) in
      let majority = xor3 (logand !a !b) (logand !a !c) (logand !b !c) in
      let second = add large0 majority in
      h := !g; g := !f; f := !e; e := add !d first;
      d := !c; c := !b; b := !a; a := add first second
    done;
    state.(0) <- add state.(0) !a; state.(1) <- add state.(1) !b;
    state.(2) <- add state.(2) !c; state.(3) <- add state.(3) !d;
    state.(4) <- add state.(4) !e; state.(5) <- add state.(5) !f;
    state.(6) <- add state.(6) !g; state.(7) <- add state.(7) !h
  done;
  String.concat "" (Array.to_list (Array.map (Printf.sprintf "%08lx") state))

type session_analysis = {
  source: string;
  revision: string;
  parsed: program option;
  checked: checked option;
  diagnostic: error option;
}

type session_document = {
  document_id: string;
  document_name: string option;
  mutable current_revision: string;
  revisions: (string, session_analysis) Hashtbl.t;
}

let session_parse_count = ref 0
let session_typecheck_count = ref 0
let session_cache_hits = ref 0

let session_metrics_json () =
  Printf.sprintf "{\"parse_count\":%d,\"typecheck_count\":%d,\"cache_hits\":%d}"
    !session_parse_count !session_typecheck_count !session_cache_hits

let analyse_session_source source =
  let revision = "sha256:" ^ sha256_hex source in
  incr session_parse_count;
  try
    let tops = parse source in
    incr session_typecheck_count;
    try
      let checked = check tops in
      { source; revision; parsed = Some tops; checked = Some checked; diagnostic = None }
    with Error diagnostic ->
      { source; revision; parsed = Some tops; checked = None; diagnostic = Some diagnostic }
  with Error diagnostic ->
    { source; revision; parsed = None; checked = None; diagnostic = Some diagnostic }

let session_status analysis =
  match analysis.diagnostic, analysis.checked with
  | Some _, _ | _, None -> "invalid"
  | None, Some checked -> program_status checked

let session_diagnostic_json diagnostic =
  Printf.sprintf "{\"code\":%s,\"severity\":\"error\",\"message\":%s,\"expectedType\":%s,\"span\":%s}"
    (json_string diagnostic.code) (json_string diagnostic.message)
    (match diagnostic.expected with None -> "null" | Some ty -> json_string (type_name ty))
    (span_json diagnostic.at)

let session_hole_json document revision hole =
  let name = match hole.hid with None -> "null" | Some value -> json_string value in
  let identity = match hole.hid with
    | None -> "null"
    | Some value ->
        Printf.sprintf "{\"document\":%s,\"revision\":%s,\"scope\":%s,\"name\":%s}"
          (json_string document) (json_string revision) (json_string hole.hscope) (json_string value)
  in
  let bindings = "[" ^ String.concat "," (List.map (fun binding ->
    Printf.sprintf "{\"name\":%s,\"bindingId\":%d,\"type\":%s,\"mutable\":%s}"
      (json_string binding.bname) binding.bid
      (match binding.bty with None -> "null" | Some ty -> json_string (type_name ty))
      (string_of_bool binding.mutable_)) hole.hbindings) ^ "]" in
  let actions = match hole.hty with
    | None -> "[]"
    | Some ty ->
        let candidates = candidates ty hole.hbindings in
        "[{\"kind\":\"fill_hole\",\"expectedType\":" ^ json_string (type_name ty) ^
        ",\"candidates\":[" ^ String.concat "," (List.map (fun binding ->
          Printf.sprintf "{\"name\":%s,\"bindingId\":%d}" (json_string binding.bname) binding.bid) candidates) ^ "]}]"
  in
  Printf.sprintf "{\"identity\":%s,\"name\":%s,\"scope\":%s,\"expectedType\":%s,\"bindings\":%s,\"actions\":%s,\"span\":%s}"
    identity name (json_string hole.hscope)
    (match hole.hty with None -> "null" | Some ty -> json_string (type_name ty))
    bindings actions (span_json hole.hspan)

let session_documents : (string, session_document) Hashtbl.t = Hashtbl.create 8
let session_member fields key = List.assoc_opt key fields

let session_required_string fields key = match session_member fields key with
  | Some (JString value) -> value
  | None -> raise (Session_error ("PEP_SESSION_FIELD_REQUIRED", "Missing string field '" ^ key ^ "'"))
  | Some _ -> raise (Session_error ("PEP_SESSION_FIELD_TYPE", "Field '" ^ key ^ "' must be a string"))

let session_optional_string fields key = match session_member fields key with
  | None | Some JNull -> None
  | Some (JString value) -> Some value
  | Some _ -> raise (Session_error ("PEP_SESSION_FIELD_TYPE", "Field '" ^ key ^ "' must be a string or null"))

let session_integer fields key = match session_member fields key with
  | Some (JNumber number) ->
      (try int_of_string number with _ -> raise (Session_error ("PEP_SESSION_FIELD_TYPE", "Field '" ^ key ^ "' must be an integer")))
  | None -> raise (Session_error ("PEP_SESSION_FIELD_REQUIRED", "Missing integer field '" ^ key ^ "'"))
  | Some _ -> raise (Session_error ("PEP_SESSION_FIELD_TYPE", "Field '" ^ key ^ "' must be an integer"))

let session_object = function
  | JObject fields -> fields
  | _ -> raise (Session_error ("PEP_SESSION_REQUEST_TYPE", "Each JSONL request must be a JSON object"))

let session_document fields =
  let id = session_required_string fields "document" in
  match Hashtbl.find_opt session_documents id with
  | None -> raise (Session_error ("PEP_DOCUMENT_NOT_FOUND", "Document identity was not opened in this session"))
  | Some document -> document

let session_get_revision document revision =
  match Hashtbl.find_opt document.revisions revision with
  | Some analysis -> analysis
  | None -> raise (Session_error ("PEP_REVISION_NOT_FOUND", "Revision is not retained in this session"))

type tool_entry = {
  tool_key:string;
  tool_protocol_version:int;
  tool_name:string;
  tool_document:string;
  tool_revision:string;
  tool_function:string;
  tool_function_id:int option;
  tool_parameters:ty list option;
  tool_result:ty option;
  tool_description:string;
  mutable tool_status:string;
  mutable tool_failure:string option;
}

let session_tools : (string, tool_entry) Hashtbl.t = Hashtbl.create 16
let session_active_tools : (string, string) Hashtbl.t = Hashtbl.create 8
let tool_step_budget = 100_000
let tool_call_depth_budget = 128

let session_tool_version fields =
  match session_member fields "toolProtocolVersion" with
  | Some (JNumber "1") -> 1
  | Some (JNumber "2") -> 2
  | Some _ -> raise (Session_error ("PEP_TOOL_PROTOCOL_VERSION", "toolProtocolVersion must be 1 or 2"))
  | None -> raise (Session_error ("PEP_SESSION_FIELD_REQUIRED", "Missing integer field 'toolProtocolVersion'"))

let session_tool_entry protocol name document revision =
  let key = name ^ "\000" ^ document ^ "\000" ^ revision ^ "\000" ^ string_of_int protocol in
  match Hashtbl.find_opt session_tools key with
  | Some entry -> entry
  | None -> raise (Session_error ("PEP_TOOL_NOT_REGISTERED", "No tool registration matches this name, revision, and protocol version"))

let session_tool_signature_json entry =
  let parameters = match entry.tool_parameters with
    | None -> "null"
    | Some types -> "[" ^ String.concat "," (List.map (fun ty -> json_string (type_name ty)) types) ^ "]"
  in
  let result = match entry.tool_result with None -> "null" | Some ty -> json_string (type_name ty) in
  "{\"parameters\":" ^ parameters ^ ",\"returns\":" ^ result ^ "}"

let session_tool_registration_json operation entry outcome =
  Printf.sprintf "{\"schemaVersion\":3,\"toolProtocolVersion\":%d,\"outcome\":%s,\"operation\":%s,\"tool\":%s,\"document\":%s,\"revision\":%s,\"function\":%s,\"signature\":%s,\"status\":%s,\"description\":%s,\"callable\":%s,\"error\":%s}"
    entry.tool_protocol_version (json_string outcome) (json_string operation) (json_string entry.tool_name)
    (json_string entry.tool_document) (json_string entry.tool_revision)
    (json_string entry.tool_function) (session_tool_signature_json entry)
    (json_string entry.tool_status) (json_string entry.tool_description)
    (if entry.tool_status = "Active" then "true" else "false")
    (match entry.tool_failure with None -> "null" | Some message -> json_string message)

let session_tool_scalar = function Int | Bool | Str | Unit -> true | List _ | Named _ -> false

let tool_value_json ty value =
  let encoded = match ty,value with
    | Int,VInt number -> json_string (Int64.to_string number)
    | Bool,VBool boolean -> if boolean then "true" else "false"
    | Str,VStr text -> if not (valid_utf8 text) then raise (Session_error ("PEP_TOOL_RESULT_ENCODING", "Str result contains invalid UTF-8 bytes")) else json_string text
    | Unit,VUnit -> "null"
    | _ -> raise (Session_error ("PEP_TOOL_RESULT_TYPE", "Interpreter result did not match the checked tool return type"))
  in
  "{\"type\":" ^ json_string (type_name ty) ^ ",\"value\":" ^ encoded ^ "}"

let session_tool_value expected = function
  | JObject fields ->
      let actual = session_required_string fields "type" in
      if actual <> type_name expected then
        raise (Session_error ("PEP_TOOL_ARGUMENT_TYPE", "Tool argument type did not match the checked parameter type"));
      let value = match expected,session_member fields "value" with
        | Int,Some (JString decimal) ->
            let digits = if String.length decimal>0 && decimal.[0]='-' then String.sub decimal 1 (String.length decimal-1) else decimal in
            if digits="" || not (String.for_all (fun c -> c>='0' && c<='9') digits) then
              raise (Session_error ("PEP_TOOL_INTEGER_FORMAT", "Int values must be signed 64-bit decimal strings"));
            (try VInt (Int64.of_string decimal) with _ -> raise (Session_error ("PEP_TOOL_INTEGER_FORMAT", "Int values must be signed 64-bit decimal strings")))
        | Bool,Some (JBool boolean) -> VBool boolean
        | Str,Some (JString text) -> VStr text
        | Unit,Some JNull -> VUnit
        | _ -> raise (Session_error ("PEP_TOOL_ARGUMENT_VALUE", "Tool argument value did not match its declared scalar type"))
      in value
  | _ -> raise (Session_error ("PEP_TOOL_ARGUMENT_VALUE", "Each tool argument must be a typed value object"))

let tool_v2_max_depth = 16
let tool_v2_max_nodes = 10_000
let tool_message_max_bytes = 1_048_576

let session_exact_fields fields expected code =
  if List.map fst fields <> expected then
    raise (Session_error (code, "Typed value fields must appear exactly once and in the declared order"))

let session_record_by_name checked name =
  match List.find_opt (fun info -> info.record_name=name) checked.records with
  |Some info->Some info
  |None->List.find_opt(fun info->info.record_name=name)semantic_record_infos

let session_tool_transport_supported checked ty =
  let rec supports seen = function
    |Int|Bool|Str|Unit->true
    |List element->supports seen element
    |Named name->
        (match session_record_by_name checked name with
         |None->false
         |Some info when List.mem name seen->true
         |Some info->List.for_all(fun(_,_,field_type,_)->supports(name::seen)field_type)info.record_fields)
  in supports [] ty

let session_scalar_json ty value =
  let encoded = match ty,value with
    | Int,VInt number -> json_string (Int64.to_string number)
    | Bool,VBool boolean -> if boolean then "true" else "false"
    | Str,VStr text -> if not (valid_utf8 text) then raise (Session_error ("PEP_TOOL_RESULT_ENCODING", "Str result contains invalid UTF-8 bytes")) else json_string text
    | Unit,VUnit -> "null"
    | _ -> raise (Session_error ("PEP_TOOL_RESULT_TYPE", "Interpreter result did not match the checked tool return type"))
  in
  "{" ^ json_string "type" ^ ":" ^ json_string (type_name ty) ^ "," ^ json_string "value" ^ ":" ^ encoded ^ "}"

let tool_value_json_v2 checked ty value =
  let remaining=ref tool_v2_max_nodes in
  let charge () = decr remaining; if !remaining<0 then raise (Session_error ("PEP_TOOL_VALUE_LIMIT", "Typed tool value exceeds the element budget")) in
  let rec encode depth expected actual =
    if depth>tool_v2_max_depth then raise (Session_error ("PEP_TOOL_VALUE_DEPTH", "Typed tool value exceeds the nesting limit"));
    charge ();
    match expected,actual with
    |(Int|Bool|Str|Unit),_ -> session_scalar_json expected actual
    |List element,VList values ->
        let items=List.map (encode (depth+1) element) values in
        "{" ^ json_string "type" ^ ":" ^ json_string(type_name expected) ^ "," ^ json_string "value" ^ ":[" ^ String.concat "," items ^ "]}"
    |Named name,VRecord(id,values) ->
        (match session_record_by_name checked name with
         |Some info when info.record_id=id ->
            let fields=List.map(fun(field_id,field_name,field_type,_)->
              let field_value=try List.assoc field_id values with Not_found->raise(Session_error("PEP_TOOL_RESULT_TYPE","Record result is missing a declared field")) in
              "{" ^ json_string "name" ^ ":" ^ json_string field_name ^ "," ^ json_string "value" ^ ":" ^ encode (depth+1) field_type field_value ^ "}")info.record_fields in
            "{" ^ json_string "type" ^ ":" ^ json_string name ^ "," ^ json_string "fields" ^ ":[" ^ String.concat "," fields ^ "]}"
         |_ -> raise (Session_error ("PEP_TOOL_RESULT_TYPE", "Record result did not match the checked tool return type")))
    |_ -> raise (Session_error ("PEP_TOOL_RESULT_TYPE", "Interpreter result did not match the checked tool return type"))
  in encode 0 ty value

let session_tool_value_v2 checked expected payload =
  let remaining=ref tool_v2_max_nodes in
  let charge () = decr remaining; if !remaining<0 then raise (Session_error ("PEP_TOOL_VALUE_LIMIT", "Typed tool value exceeds the element budget")) in
  let scalar ty json = match ty,json with
    | Int,JString decimal ->
        let digits = if String.length decimal>0 && decimal.[0]='-' then String.sub decimal 1 (String.length decimal-1) else decimal in
        if digits="" || not (String.for_all (fun c -> c>='0' && c<='9') digits) then
          raise (Session_error ("PEP_TOOL_INTEGER_FORMAT", "Int values must be signed 64-bit decimal strings"));
        (try VInt (Int64.of_string decimal) with _ -> raise (Session_error ("PEP_TOOL_INTEGER_FORMAT", "Int values must be signed 64-bit decimal strings")))
    | Bool,JBool boolean -> VBool boolean
    | Str,JString text -> VStr text
    | Unit,JNull -> VUnit
    | _ -> raise (Session_error ("PEP_TOOL_ARGUMENT_VALUE", "Tool argument value did not match its declared type"))
  in
  let rec decode depth ty payload =
    if depth>tool_v2_max_depth then raise (Session_error ("PEP_TOOL_VALUE_DEPTH", "Typed tool value exceeds the nesting limit"));
    charge ();
    match payload with
    |JObject fields ->
       let actual=session_required_string fields "type" in
       if actual<>type_name ty then raise (Session_error ("PEP_TOOL_ARGUMENT_TYPE", "Tool argument type did not match the checked parameter type"));
       (match ty with
        |Int|Bool|Str|Unit ->
           session_exact_fields fields ["type";"value"] "PEP_TOOL_VALUE_FIELDS";
           scalar ty (Option.value (session_member fields "value") ~default:JNull)
        |List element ->
           session_exact_fields fields ["type";"value"] "PEP_TOOL_VALUE_FIELDS";
           (match session_member fields "value" with
            |Some (JArray values)->VList(List.map(decode (depth+1) element)values)
            |_ ->raise(Session_error("PEP_TOOL_ARGUMENT_VALUE","List value must be an array of typed values")))
        |Named name ->
           session_exact_fields fields ["type";"fields"] "PEP_TOOL_VALUE_FIELDS";
           (match session_record_by_name checked name,session_member fields "fields" with
            |Some info,Some (JArray supplied_fields) ->
               if List.length supplied_fields<>List.length info.record_fields then raise(Session_error("PEP_TOOL_ARGUMENT_FIELDS","Record fields do not match the checked record type"));
               let values=List.map2(fun field item ->
                 let item_fields=match item with JObject values->values|_->raise(Session_error("PEP_TOOL_ARGUMENT_FIELDS","Each record field must be an object")) in
                 session_exact_fields item_fields ["name";"value"] "PEP_TOOL_ARGUMENT_FIELDS";
                 let supplied=session_required_string item_fields "name" in
                 let (field_id,field_name,field_type,_)=field in
                 if supplied<>field_name then raise(Session_error("PEP_TOOL_ARGUMENT_FIELDS","Record fields must match the declared names and order"));
                 field_id,decode (depth+1) field_type (Option.value(session_member item_fields "value")~default:JNull)
               )info.record_fields supplied_fields in
               VRecord(info.record_id,values)
            |_ ->raise(Session_error("PEP_TOOL_ARGUMENT_VALUE","Record value does not match a checked record type"))))
    |_ ->raise(Session_error("PEP_TOOL_ARGUMENT_VALUE","Each tool argument must be a typed value object"))
  in decode 0 expected payload

let rec tool_expr_calls expression =
  let child_calls = match expression.node with
    | XCall (_,_,args) -> List.concat_map tool_expr_calls args
    | XBin (_,left,right) -> tool_expr_calls left @ tool_expr_calls right
    | XIf (condition,yes,no) -> tool_expr_calls condition @ tool_expr_calls yes @ tool_expr_calls no
    | XRecord (_,fields) -> List.concat_map (fun (_,value) -> tool_expr_calls value) fields
    | XField (_,value) -> tool_expr_calls value
    | XConstructor (_,_,_,args) -> List.concat_map tool_expr_calls args
    | XMatch (subject,arms) -> tool_expr_calls subject @ List.concat_map (fun arm -> tool_expr_calls arm.tresult) arms
    | XUnary (_,value) -> tool_expr_calls value
    | XList items -> List.concat_map tool_expr_calls items
    | XInt _ | XBool _ | XStr _ | XVar _ | XHole _ -> []
  in
  let own = match expression.node with XCall (id,name,_) -> [id,name] | _ -> [] in
  own @ child_calls

let rec tool_stmt_calls = function
  | TLet (_,expression) | TVar (_,expression) | TReturn expression | TExpr expression -> tool_expr_calls expression
  | TAssign (_,expression,_) -> tool_expr_calls expression
  | TIf (condition,yes,no,_) -> tool_expr_calls condition @ List.concat_map tool_stmt_calls yes @ List.concat_map tool_stmt_calls no
  | TFor (_,iterable,body,_) -> tool_expr_calls iterable @ List.concat_map tool_stmt_calls body
  | TWhile (condition,body,_) -> tool_expr_calls condition @ List.concat_map tool_stmt_calls body
  | TBlock statements -> List.concat_map tool_stmt_calls statements

let tool_reaches_say checked function_id =
  let functions = Hashtbl.create 16 in
  List.iter (fun function_ -> Hashtbl.replace functions function_.sig_.fid function_) checked.functions;
  let rec visit seen id =
    if List.mem id seen then false
    else match Hashtbl.find_opt functions id with
      | None -> false
      | Some function_ ->
          let calls = List.concat_map tool_stmt_calls function_.tbody in
          List.exists (fun (_,name) -> name="say") calls ||
          List.exists (function Some child,_ -> visit (id::seen) child | None,_ -> false) calls
  in visit [] function_id

let tool_semantic_record checked name values =
  match session_record_by_name checked name with
  |Some info ->
      VRecord(info.record_id,List.map(fun(field_id,field_name,_,_)->field_id,List.assoc field_name values)info.record_fields)
  |None -> raise (Session_error ("PEP_TOOL_SIGNATURE_UNAVAILABLE", "Compiler semantic record type is unavailable"))

let session_semantic_target tool_checked target_message =
  let fields=match target_message with
    |JObject fields->fields
    |_ ->raise(Session_error("PEP_SEMANTIC_TARGET_TYPE","semanticTarget must be a host-provided object"))
  in
  session_exact_fields fields ["document";"revision";"entryFunctions"] "PEP_SEMANTIC_TARGET_FIELDS";
  let document_id=session_required_string fields "document" in
  let revision=session_required_string fields "revision" in
  let entry_names=match session_member fields "entryFunctions" with
    |Some (JArray values)->List.map(function JString value->value|_->raise(Session_error("PEP_SEMANTIC_ROOT_TYPE","entryFunctions must contain function names")))values
    |_ ->raise(Session_error("PEP_SEMANTIC_ROOT_TYPE","entryFunctions must be an array"))
  in
  if List.length entry_names<>List.length(List.sort_uniq compare entry_names) then
    raise(Session_error("PEP_SEMANTIC_ROOT_DUPLICATE","entryFunctions must not contain duplicate names"));
  let target_document=session_document ["document",JString document_id] in
  let analysis=session_get_revision target_document revision in
  let status=session_status analysis in
  let diagnostic_values=match analysis.diagnostic with
    |None->[]
    |Some diagnostic ->
        [tool_semantic_record tool_checked "SemanticDiagnostic"
          ["code",VStr diagnostic.code;"message",VStr diagnostic.message;
           "startByte",VInt(Int64.of_int diagnostic.at.lo);"endByte",VInt(Int64.of_int diagnostic.at.hi)]]
  in
  let functions,calls,roots=match analysis.checked with
    |None when entry_names<>[]->raise(Session_error("PEP_SEMANTIC_ROOT_UNAVAILABLE","Entry functions cannot be resolved for invalid target source"))
    |None->[],[],[]
    |Some target_checked ->
        let explicit_roots=List.map(fun name->
          match List.filter(fun function_->function_.sig_.name=name)target_checked.functions with
          |[function_]->function_.sig_.fid
          |[]->raise(Session_error("PEP_SEMANTIC_ROOT_NOT_FOUND","Host entry function does not resolve in the target revision"))
          |_ ->raise(Session_error("PEP_SEMANTIC_ROOT_AMBIGUOUS","Host entry function resolves ambiguously"))
        )entry_names in
        let unique values =
          List.fold_left(fun acc value->if List.mem value acc then acc else acc@[value])[] values
        in
        let function_values=List.map(fun function_->
          tool_semantic_record tool_checked "FunctionInfo"
            ["id",VInt(Int64.of_int function_.sig_.fid);
             "name",VStr function_.sig_.name;
             "startByte",VInt(Int64.of_int function_.sig_.decl.fspan.lo);
             "endByte",VInt(Int64.of_int function_.sig_.decl.fspan.hi)]
        )target_checked.functions in
        let edge_pairs=List.concat_map(fun function_->
          List.filter_map(function Some callee,_->Some(function_.sig_.fid,callee)|None,_->None)
            (List.concat_map tool_stmt_calls function_.tbody)
        )target_checked.functions |> unique in
        let top_roots=List.filter_map(function Some called,_->Some called|None,_->None)
          (List.concat_map tool_stmt_calls target_checked.tops) in
        let roots=unique(top_roots@explicit_roots) in
        let calls=List.map(fun(caller,callee)->
          tool_semantic_record tool_checked "CallEdge"
            ["caller",VInt(Int64.of_int caller);"callee",VInt(Int64.of_int callee)]
        )edge_pairs in
        if List.length function_values+List.length calls+List.length roots+List.length diagnostic_values>tool_v2_max_nodes then
          raise(Session_error("PEP_SEMANTIC_BUDGET","Semantic snapshot exceeds the node budget"));
        function_values,calls,List.map(fun id->VInt(Int64.of_int id))roots
  in
  if List.length functions+List.length calls+List.length roots+List.length diagnostic_values>tool_v2_max_nodes then
    raise(Session_error("PEP_SEMANTIC_BUDGET","Semantic snapshot exceeds the node budget"));
  Some(tool_semantic_record tool_checked "ProgramInfo"
    ["document",VStr document_id;"revision",VStr revision;"status",VStr status;
     "functions",VList functions;"calls",VList calls;"roots",VList roots;"diagnostics",VList diagnostic_values]),
  Some(VStr analysis.source)

let tool_reaches_builtin checked function_id builtin =
  let functions=Hashtbl.create 16 in
  List.iter(fun function_->Hashtbl.replace functions function_.sig_.fid function_)checked.functions;
  let rec visit seen id =
    if List.mem id seen then false
    else match Hashtbl.find_opt functions id with
      |None->false
      |Some function_->
          let calls=List.concat_map tool_stmt_calls function_.tbody in
          List.exists(fun(_,name)->name=builtin)calls ||
          List.exists(function Some child,_->visit(id::seen)child|None,_->false)calls
  in visit [] function_id

let tool_reaches_semantic_snapshot checked function_id = tool_reaches_builtin checked function_id "semantic_snapshot"
let tool_reaches_source_bytes checked function_id = tool_reaches_builtin checked function_id "source_bytes"

let tool_host_policy checked entry =
  match entry.tool_parameters,entry.tool_result,entry.tool_function_id with
  | Some parameters,Some result,Some function_id ->
      if entry.tool_protocol_version=1 && tool_reaches_semantic_snapshot checked function_id then Some "semantic_snapshot requires tool protocol version 2"
      else if entry.tool_protocol_version=1 && tool_reaches_source_bytes checked function_id then Some "source_bytes requires tool protocol version 2"
      else if entry.tool_protocol_version=1 && not (List.for_all session_tool_scalar (result::parameters)) then Some "Only Int, Bool, Str, and Unit may cross the v1 tool boundary"
      else if entry.tool_protocol_version=2 && not (List.for_all (session_tool_transport_supported checked) (result::parameters)) then Some "Version 2 supports only scalar, List, and monomorphic record values"
      else if tool_reaches_say checked function_id then Some "Exported function reaches say and is not permitted for tool execution"
      else None
  | _ -> Some "Tool has no checked function signature"

let tool_replacement_policy entry =
  match Hashtbl.find_opt session_active_tools entry.tool_name with
  | None -> None
  | Some active_key when active_key=entry.tool_key -> None
  | Some active_key ->
      (match Hashtbl.find_opt session_tools active_key with
       | Some active when active.tool_parameters=entry.tool_parameters && active.tool_result=entry.tool_result -> None
       | Some _ -> Some "Replacement signature is incompatible with the active tool"
       | None -> None)

let tool_find_function checked name = List.find_opt (fun function_ -> function_.sig_.name=name) checked.functions

let session_tool_register fields =
  let protocol=session_tool_version fields in
  let name = session_required_string fields "tool" in
  let document = session_document fields in
  let revision = session_required_string fields "revision" in
  let function_name = session_required_string fields "function" in
  let description = match session_member fields "description" with None -> "" | Some (JString value) -> value | Some _ -> raise (Session_error ("PEP_SESSION_FIELD_TYPE", "Field 'description' must be a string")) in
  let analysis = session_get_revision document revision in
  let key = name ^ "\000" ^ document.document_id ^ "\000" ^ revision ^ "\000" ^ string_of_int protocol in
  let entry = match analysis.checked with
    | None -> {tool_key=key;tool_protocol_version=protocol;tool_name=name;tool_document=document.document_id;tool_revision=revision;tool_function=function_name;tool_function_id=None;tool_parameters=None;tool_result=None;tool_description=description;tool_status="Rejected";tool_failure=Some "Source is invalid and has no checked function signature"}
    | Some checked ->
        (match tool_find_function checked function_name with
         | None -> raise (Session_error ("PEP_TOOL_FUNCTION_NOT_FOUND", "No checked function with this name exists at the registered revision"))
         | Some function_ ->
             {tool_key=key;tool_protocol_version=protocol;tool_name=name;tool_document=document.document_id;tool_revision=revision;tool_function=function_name;tool_function_id=Some function_.sig_.fid;tool_parameters=Some (List.map snd function_.sig_.params);tool_result=Some function_.sig_.result;tool_description=description;tool_status="Registered";tool_failure=None})
  in
  if Hashtbl.mem session_tools key then raise (Session_error ("PEP_TOOL_ALREADY_REGISTERED", "This tool name and source revision are already registered"));
  Hashtbl.add session_tools key entry;
  session_tool_registration_json "tool_register" entry (if entry.tool_status="Rejected" then "rejected" else "ok")

let session_tool_test_vector checked entry vector =
  let fields = session_object vector in
  let expected_fields=if entry.tool_protocol_version=1 then ["arguments";"expect"] else
    match List.map fst fields with
    |["arguments";"expect"]->["arguments";"expect"]
    |["arguments";"expect";"semanticTarget"]->["arguments";"expect";"semanticTarget"]
    |_ -> raise (Session_error ("PEP_TOOL_TEST_VECTOR", "Version 2 test vectors must contain arguments, expect, and optional semanticTarget in order"))
  in
  session_exact_fields fields expected_fields "PEP_TOOL_TEST_VECTOR";
  let args = match session_member fields "arguments" with Some (JArray values) -> values | _ -> raise (Session_error ("PEP_TOOL_TEST_VECTOR", "Each test vector requires an arguments array")) in
  let snapshot,source_bytes=match session_member fields "semanticTarget" with
    |None->None,None
    |Some target->session_semantic_target checked target
  in
  match entry.tool_parameters,entry.tool_result,entry.tool_function_id with
  |Some parameters,Some result,Some function_id ->
     if List.length parameters <> List.length args then raise (Session_error ("PEP_TOOL_ARGUMENT_COUNT", "Test vector argument count did not match the function signature"));
     let decode=if entry.tool_protocol_version=1 then session_tool_value else session_tool_value_v2 checked in
     let values = List.map2 decode parameters args in
     let expected_json = match session_member fields "expect" with Some value -> value | None -> raise (Session_error ("PEP_TOOL_TEST_VECTOR", "Each test vector requires an expect value")) in
     let expected_value = decode result expected_json in
     let actual = execute ~entry:(Some (function_id,values)) ~allow_say:false ~step_limit:tool_step_budget ~max_depth:tool_call_depth_budget ~semantic_snapshot_value:snapshot ~source_bytes_value:source_bytes checked in
     if actual <> expected_value then raise (Session_error ("PEP_TOOL_TEST_FAILED", "Interpreter result did not match the expected test vector"))
  | _ -> raise (Session_error ("PEP_TOOL_SIGNATURE_UNAVAILABLE", "Tool has no checked function signature"))

let session_tool_validate fields =
  let protocol=session_tool_version fields in
  let entry = session_tool_entry protocol (session_required_string fields "tool") (session_required_string fields "document") (session_required_string fields "revision") in
  if entry.tool_status="Active" || entry.tool_status="Superseded" then
    raise (Session_error ("PEP_TOOL_STATE", "Active and superseded registrations cannot be revalidated"));
  let analysis = session_get_revision (session_document ["document",JString entry.tool_document]) entry.tool_revision in
  let reject message = entry.tool_status <- "Rejected"; entry.tool_failure <- Some message in
  (match analysis.checked with
   | None -> reject "Source is invalid and cannot be validated"
   | Some checked when session_status analysis <> "valid" -> reject "Incomplete source cannot be activated"
   | Some checked ->
       (match tool_host_policy checked entry with
        | Some reason -> reject reason
        | None -> (match tool_replacement_policy entry with
            | Some reason -> reject reason
            | None -> (match session_member fields "testVectors" with
                | Some (JArray (_::_ as vectors)) ->
                    (try List.iter (session_tool_test_vector checked entry) vectors; entry.tool_status <- "Validated"; entry.tool_failure <- None
                     with Session_error (code,message) -> reject (code^": "^message) | Runtime (code,message,_) -> reject (code^": "^message))
                | _ -> reject "Validation requires at least one real interpreter test vector"))));
  session_tool_registration_json "tool_validate" entry (if entry.tool_status="Validated" then "ok" else "rejected")

let session_tool_activate fields =
  let protocol=session_tool_version fields in
  let entry = session_tool_entry protocol (session_required_string fields "tool") (session_required_string fields "document") (session_required_string fields "revision") in
  if entry.tool_status <> "Validated" then raise (Session_error ("PEP_TOOL_NOT_VALIDATED", "Only a successfully validated tool can be activated"));
  (match Hashtbl.find_opt session_active_tools entry.tool_name with
   | Some previous_key when previous_key <> entry.tool_key ->
       (match Hashtbl.find_opt session_tools previous_key with Some previous -> previous.tool_status <- "Superseded" | None -> ())
   | _ -> ());
  entry.tool_status <- "Active";
  entry.tool_failure <- None;
  Hashtbl.replace session_active_tools entry.tool_name entry.tool_key;
  session_tool_registration_json "tool_activate" entry "ok"

let session_tool_list fields =
  let protocol=session_tool_version fields in
  let entries = Hashtbl.fold (fun _ entry acc -> entry::acc) session_tools [] |> List.sort (fun a b -> compare (a.tool_name,a.tool_revision,a.tool_protocol_version) (b.tool_name,b.tool_revision,b.tool_protocol_version)) in
  let rows = List.map (fun entry ->
    let active_revision = match Hashtbl.find_opt session_active_tools entry.tool_name with
      | Some key -> (match Hashtbl.find_opt session_tools key with Some active -> json_string active.tool_revision | None -> "null")
      | None -> "null" in
    Printf.sprintf "{\"toolProtocolVersion\":%d,\"tool\":%s,\"document\":%s,\"revision\":%s,\"activeRevision\":%s,\"function\":%s,\"signature\":%s,\"description\":%s,\"status\":%s,\"callable\":%s}"
      entry.tool_protocol_version (json_string entry.tool_name) (json_string entry.tool_document) (json_string entry.tool_revision)
      active_revision (json_string entry.tool_function) (session_tool_signature_json entry) (json_string entry.tool_description)
      (json_string entry.tool_status) (if entry.tool_status="Active" then "true" else "false")) entries in
  Printf.sprintf "{\"schemaVersion\":3,\"toolProtocolVersion\":%d,\"outcome\":\"ok\",\"operation\":\"tool_list\",\"tools\":[%s]}" protocol (String.concat "," rows)

let session_tool_invoke fields =
  let protocol=session_tool_version fields in
  let name = session_required_string fields "tool" in
  let key = match Hashtbl.find_opt session_active_tools name with Some key -> key | None -> raise (Session_error ("PEP_TOOL_NOT_ACTIVE", "No active tool has this name")) in
  let entry = match Hashtbl.find_opt session_tools key with Some entry when entry.tool_status="Active" -> entry | _ -> raise (Session_error ("PEP_TOOL_NOT_ACTIVE", "Tool does not have an active registry entry")) in
  if entry.tool_protocol_version<>protocol then raise(Session_error("PEP_TOOL_PROTOCOL_MISMATCH","Invocation protocol version must match the active registration"));
  let args = match session_member fields "arguments" with Some (JArray values) -> values | _ -> raise (Session_error ("PEP_TOOL_ARGUMENTS", "Invocation requires an arguments array")) in
  let analysis = session_get_revision (session_document ["document",JString entry.tool_document]) entry.tool_revision in
  let checked = match analysis.checked,entry.tool_function_id with Some checked,Some _ -> checked | _ -> raise (Session_error ("PEP_TOOL_SOURCE_UNAVAILABLE", "Active tool source revision is unavailable")) in
  let values = match entry.tool_parameters with
    | Some parameters when List.length parameters=List.length args ->
        let decode=if protocol=1 then session_tool_value else session_tool_value_v2 checked in
        List.map2 decode parameters args
    | Some _ -> raise (Session_error ("PEP_TOOL_ARGUMENT_COUNT", "Tool argument count did not match its signature"))
    | None -> raise (Session_error ("PEP_TOOL_SIGNATURE_UNAVAILABLE", "Active tool has no checked signature"))
  in
  let snapshot,source_bytes=match session_member fields "semanticTarget" with
    |None->None,None
    |Some _ when protocol=1->raise(Session_error("PEP_TOOL_PROTOCOL_MISMATCH","semanticTarget requires tool protocol version 2"))
    |Some target->session_semantic_target checked target
  in
  let encoded_result = match entry.tool_function_id,entry.tool_result with
    | Some function_id,Some result_type ->
        let value = execute ~entry:(Some (function_id,values)) ~allow_say:false ~step_limit:tool_step_budget ~max_depth:tool_call_depth_budget ~semantic_snapshot_value:snapshot ~source_bytes_value:source_bytes checked in
        if protocol=1 then tool_value_json result_type value else tool_value_json_v2 checked result_type value
    | _ -> raise (Session_error ("PEP_TOOL_SIGNATURE_UNAVAILABLE", "Active tool has no checked function signature"))
  in
  if String.length encoded_result>tool_message_max_bytes then raise(Session_error("PEP_TOOL_MESSAGE_TOO_LARGE","Tool result exceeds the response byte budget"));
  Printf.sprintf "{\"schemaVersion\":3,\"toolProtocolVersion\":%d,\"outcome\":\"ok\",\"operation\":\"tool_invoke\",\"tool\":%s,\"revision\":%s,\"result\":%s}"
    protocol (json_string entry.tool_name) (json_string entry.tool_revision) encoded_result

let session_response operation document revision analysis ?offset ?(extra="") () =
  let holes = match analysis.checked with
    | None -> []
    | Some checked ->
        (match offset with
         | None -> checked.holes
         | Some byte -> List.filter (fun hole -> hole.hspan.lo = byte) checked.holes)
  in
  let ast = match analysis.parsed with None -> "null" | Some tops -> ast_json tops in
  let typed = match analysis.checked with None -> "null" | Some checked -> typed_json checked in
  let diagnostics = match analysis.diagnostic with None -> "[]" | Some diagnostic -> "[" ^ session_diagnostic_json diagnostic ^ "]" in
  Printf.sprintf "{\"schemaVersion\":3,\"outcome\":\"ok\",\"operation\":%s,\"document\":%s,\"name\":%s,\"revision\":%s,\"status\":%s,\"ast\":%s,\"typedTree\":%s,\"holes\":[%s],\"diagnostics\":%s%s}"
    (json_string operation) (json_string document)
    (match Hashtbl.find_opt session_documents document with
     | Some doc -> (match doc.document_name with None -> "null" | Some name -> json_string name)
     | None -> "null")
    (json_string revision) (json_string (session_status analysis)) ast typed
    (String.concat "," (List.map (session_hole_json document revision) holes)) diagnostics extra

let session_error_json operation code message ?document ?current_revision ?(tool_protocol_version=1) () =
  let optional key = function None -> "" | Some value -> ",\"" ^ key ^ "\":" ^ json_string value in
  let tool_version = match operation with
    | Some ("tool_register" | "tool_validate" | "tool_activate" | "tool_list" | "tool_invoke") -> Printf.sprintf ",\"toolProtocolVersion\":%d" tool_protocol_version
    | _ -> ""
  in
  Printf.sprintf "{\"schemaVersion\":3,\"outcome\":\"error\",\"operation\":%s%s,\"error\":{\"code\":%s,\"message\":%s}%s%s,\"metrics\":%s}"
    (match operation with None -> "null" | Some op -> json_string op)
    tool_version (json_string code) (json_string message)
    (optional "document" document) (optional "currentRevision" current_revision)
    (session_metrics_json ())

let session_revision source = "sha256:" ^ sha256_hex source

let session_analyse_or_reuse document source =
  let revision = session_revision source in
  match Hashtbl.find_opt document.revisions revision with
  | Some analysis when analysis.source = source -> incr session_cache_hits; analysis
  | Some _ -> raise (Session_error ("PEP_REVISION_HASH_COLLISION", "SHA-256 revision collision detected; source was not changed"))
  | None ->
      let analysis = analyse_session_source source in
      Hashtbl.add document.revisions revision analysis;
      analysis

let session_is_boundary source offset =
  offset = 0 || offset = String.length source || Char.code source.[offset] land 0xc0 <> 0x80

let session_splice_source source start_byte end_byte replacement =
  let buffer = Buffer.create (String.length source - (end_byte - start_byte) + String.length replacement) in
  Buffer.add_substring buffer source 0 start_byte;
  Buffer.add_string buffer replacement;
  Buffer.add_substring buffer source end_byte (String.length source - end_byte);
  Buffer.contents buffer

let session_apply_edit document fields =
  let expected = session_required_string fields "expected_revision" in
  if expected <> document.current_revision then
    raise (Session_error ("PEP_STALE_REVISION", "Edit expected a revision other than the document's current revision"));
  let start_byte = session_integer fields "start_byte" and end_byte = session_integer fields "end_byte" in
  let replacement = session_required_string fields "replacement" in
  let current = session_get_revision document document.current_revision in
  let source_length = String.length current.source in
  if start_byte < 0 || end_byte < start_byte || end_byte > source_length then
    raise (Session_error ("PEP_INVALID_EDIT_RANGE", "Edit range must be a half-open byte range within the source"));
  if not (valid_utf8 replacement) then
    raise (Session_error ("PEP_INVALID_UTF8", "Replacement must contain valid UTF-8"));
  if not (session_is_boundary current.source start_byte && session_is_boundary current.source end_byte) then
    raise (Session_error ("PEP_UTF8_BOUNDARY", "Edit range splits a UTF-8 code point"));
  let new_source = session_splice_source current.source start_byte end_byte replacement in
  let analysis = session_analyse_or_reuse document new_source in
  Hashtbl.replace document.revisions analysis.revision analysis;
  document.current_revision <- analysis.revision;
  session_response "apply_edit" document.document_id analysis.revision analysis ()

let session_fill_rejection operation mode document base_revision candidate_revision candidate_status message source_diff diagnostics =
  Printf.sprintf "{\"schemaVersion\":3,\"outcome\":\"rejected\",\"operation\":%s,\"mode\":%s,\"document\":%s,\"currentRevision\":%s,\"candidateRevision\":%s,\"candidateStatus\":%s,\"message\":%s,\"sourceDiff\":%s,\"diagnostics\":%s,\"metrics\":%s}"
    (json_string operation) (json_string mode) (json_string document.document_id)
    (json_string base_revision)
    (match candidate_revision with None -> "null" | Some revision -> json_string revision)
    (match candidate_status with None -> "null" | Some status -> json_string status)
    (json_string message) source_diff diagnostics (session_metrics_json ())

let session_fill_hole document fields =
  let operation = "fill_hole" in
  let expected = session_required_string fields "expected_revision" in
  if expected <> document.current_revision then
    session_error_json (Some operation) "PEP_STALE_REVISION"
      "Structural edit expected a revision other than the document's current revision"
      ~document:document.document_id ~current_revision:document.current_revision ()
  else
    let scope = session_required_string fields "scope" in
    let name = session_required_string fields "name" in
    let replacement = session_required_string fields "replacement" in
    let mode = session_required_string fields "mode" in
    if mode <> "preview" && mode <> "apply" then
      raise (Session_document_error ("PEP_FILL_HOLE_MODE", "Mode must be 'preview' or 'apply'", document.document_id, document.current_revision));
    if not (valid_utf8 replacement) then
      raise (Session_document_error ("PEP_INVALID_UTF8", "Replacement must contain valid UTF-8", document.document_id, document.current_revision));
    let current = session_get_revision document document.current_revision in
    match current.checked with
    | None ->
        raise (Session_document_error ("PEP_DOCUMENT_INVALID", "Cannot structurally edit a document without a checked semantic tree", document.document_id, document.current_revision))
    | Some checked ->
        let matches = List.filter (fun hole -> hole.hscope = scope && hole.hid = Some name) checked.holes in
        let hole = match matches with
          | [] -> raise (Session_document_error ("PEP_HOLE_NOT_FOUND", "No named hole matches the supplied scope and name", document.document_id, document.current_revision))
          | [hole] -> hole
          | _ -> raise (Session_document_error ("PEP_HOLE_AMBIGUOUS", "More than one named hole matches the supplied scope and name", document.document_id, document.current_revision))
        in
        let start_byte = hole.hspan.lo and end_byte = hole.hspan.hi in
        let old_text = String.sub current.source start_byte (end_byte - start_byte) in
        let source_diff = Printf.sprintf "{\"startByte\":%d,\"endByte\":%d,\"removed\":%s,\"inserted\":%s}"
          start_byte end_byte (json_string old_text) (json_string replacement) in
        let candidate_source = session_splice_source current.source start_byte end_byte replacement in
        (try
           ignore (parse_single_expression replacement);
           let candidate = analyse_session_source candidate_source in
           let status = session_status candidate in
           match candidate.diagnostic with
           | Some diagnostic ->
               session_fill_rejection operation mode document document.current_revision
                 (Some candidate.revision) (Some status) diagnostic.message source_diff
                 ("[" ^ session_diagnostic_json diagnostic ^ "]")
           | None ->
               let extra = Printf.sprintf ",\"mode\":%s,\"baseRevision\":%s,\"currentRevision\":%s,\"sourceDiff\":%s"
                 (json_string mode) (json_string document.current_revision)
                 (json_string (if mode = "apply" then candidate.revision else document.current_revision)) source_diff in
               if mode = "preview" then
                 session_response operation document.document_id candidate.revision candidate ~extra ()
               else (
                 Hashtbl.replace document.revisions candidate.revision candidate;
                 document.current_revision <- candidate.revision;
                 session_response operation document.document_id candidate.revision candidate ~extra ())
         with Error diagnostic ->
           session_fill_rejection operation mode document document.current_revision None (Some "invalid")
             diagnostic.message source_diff ("[" ^ session_diagnostic_json diagnostic ^ "]"))

let session_process request =
  let fields = session_object request in
  let schema = session_integer fields "schemaVersion" in
  if schema <> 3 then raise (Session_error ("PEP_SESSION_SCHEMA_VERSION", "This session supports schemaVersion 3"));
  let operation = session_required_string fields "op" in
  match operation with
  | "open" ->
      let source = session_required_string fields "source" in
      if not (valid_utf8 source) then raise (Session_error ("PEP_INVALID_UTF8", "Source must contain valid UTF-8"));
      let name = session_optional_string fields "name" in
      let next = (Hashtbl.length session_documents) + 1 in
      let document_id = "doc-" ^ string_of_int next in
      if Hashtbl.mem session_documents document_id then raise (Session_error ("PEP_DOCUMENT_ID_EXHAUSTED", "Could not allocate a session document identity"));
      let analysis = analyse_session_source source in
      let document = { document_id; document_name = name; current_revision = analysis.revision; revisions = Hashtbl.create 8 } in
      Hashtbl.add document.revisions analysis.revision analysis;
      Hashtbl.add session_documents document_id document;
      session_response operation document_id analysis.revision analysis ()
  | "open_bytes" ->
      let byte_values=match session_member fields "bytes" with
        |Some (JArray values)->values
        |_ ->raise (Session_error ("PEP_SOURCE_BYTES_TYPE", "open_bytes requires a bytes array of unsigned integers"))
      in
      if List.length byte_values>65536 then raise (Session_error ("PEP_SOURCE_BYTE_LIMIT", "Source byte input exceeds 65536 bytes"));
      let buffer=Buffer.create (List.length byte_values) in
      List.iter (function
        |JNumber number->(try let byte=int_of_string number in if byte<0 || byte>255 then raise Exit;Buffer.add_char buffer (Char.chr byte)
          with _->raise (Session_error ("PEP_SOURCE_BYTE_VALUE", "Each source byte must be an integer from 0 through 255")))
        |_ ->raise (Session_error ("PEP_SOURCE_BYTE_VALUE", "Each source byte must be an integer from 0 through 255"))) byte_values;
      let source=Buffer.contents buffer in
      let name=session_optional_string fields "name" in
      let next=(Hashtbl.length session_documents)+1 in
      let document_id="doc-"^string_of_int next in
      if Hashtbl.mem session_documents document_id then raise (Session_error ("PEP_DOCUMENT_ID_EXHAUSTED", "Could not allocate a session document identity"));
      let analysis=analyse_session_source source in
      let document={document_id;document_name=name;current_revision=analysis.revision;revisions=Hashtbl.create 8} in
      Hashtbl.add document.revisions analysis.revision analysis;
      Hashtbl.add session_documents document_id document;
      session_response operation document_id analysis.revision analysis ()
  | "query" | "inspect" ->
      let document = session_document fields in
      let revision = session_required_string fields "revision" in
      let analysis = session_get_revision document revision in
      incr session_cache_hits;
      let offset = match session_member fields "offset" with
        | None | Some JNull -> None
        | Some (JNumber number) ->
            (try let value = int_of_string number in if value < 0 then raise Exit; Some value
             with _ -> raise (Session_error ("PEP_SESSION_FIELD_TYPE", "Field 'offset' must be a nonnegative integer")))
        | Some _ -> raise (Session_error ("PEP_SESSION_FIELD_TYPE", "Field 'offset' must be an integer"))
      in
      session_response operation document.document_id revision analysis ?offset ()
  | "apply_edit" ->
      let document = session_document fields in
      let expected = session_required_string fields "expected_revision" in
      if expected <> document.current_revision then
        session_error_json (Some operation) "PEP_STALE_REVISION"
          "Edit expected a revision other than the document's current revision"
          ~document:document.document_id ~current_revision:document.current_revision ()
      else session_apply_edit document fields
  | "fill_hole" ->
      let document = session_document fields in
      session_fill_hole document fields
  | "tool_register" -> session_tool_register fields
  | "tool_validate" -> session_tool_validate fields
  | "tool_activate" -> session_tool_activate fields
  | "tool_list" -> session_tool_list fields
  | "tool_invoke" -> session_tool_invoke fields
  | "metrics" ->
      Printf.sprintf "{\"schemaVersion\":3,\"outcome\":\"ok\",\"operation\":\"metrics\",\"metrics\":%s}"
        (session_metrics_json ())
  | _ -> raise (Session_error ("PEP_SESSION_UNKNOWN_OPERATION", "Unsupported session operation '" ^ operation ^ "'"))

let session_operation_hint = function
  | JObject fields -> (match session_member fields "op" with Some (JString op) -> Some op | _ -> None)
  | _ -> None

let session_tool_version_hint request =
  match request with
  |JObject fields->(match session_member fields "toolProtocolVersion" with Some(JNumber "2")->2|_->1)
  |_ ->1

let run_session_jsonl () =
  let rec loop () =
    try
      let line = input_line stdin in
      let response =
        if String.length line>tool_message_max_bytes then
          session_error_json None "PEP_TOOL_MESSAGE_TOO_LARGE" "JSONL request exceeds the message byte budget" ()
        else
          try
            let request = parse_json line in
            let protocol=session_tool_version_hint request in
            let result=try session_process request with
              | Session_error (code, message) ->
                  session_error_json (session_operation_hint request) code message ~tool_protocol_version:protocol ()
              | Session_document_error (code, message, document, revision) ->
                  session_error_json (session_operation_hint request) code message
                    ~document ~current_revision:revision ~tool_protocol_version:protocol ()
              | Runtime (code,message,span) ->
                  session_error_json (session_operation_hint request) code
                    (Printf.sprintf "%s at %d:%d" message span.line span.column) ~tool_protocol_version:protocol ()
            in
            if String.length result>tool_message_max_bytes then
              session_error_json (session_operation_hint request) "PEP_TOOL_MESSAGE_TOO_LARGE"
                "JSONL response exceeds the message byte budget" ~tool_protocol_version:protocol ()
            else result
          with Json_parse_error message -> session_error_json None "PEP_SESSION_MALFORMED_JSON" message ()
      in
      print_endline response;
      flush stdout;
      loop ()
    with End_of_file -> ()
  in
  loop ()

let read_file path = let ic=open_in_bin path in Fun.protect ~finally:(fun()->close_in ic)(fun()->really_input_string ic (in_channel_length ic))
let usage () = prerr_endline "usage: pep describe [--json] | inspect|check|run FILE [--json] | query FILE --holes --json [--offset N] | session --jsonl";exit 2
let () =
 try
  let args=Array.to_list Sys.argv |> List.tl in
  match args with
  |["describe"]|["describe";"--json"]->print_endline "{\"schemaVersion\":2,\"language\":\"Pep\",\"types\":[\"Int\",\"Bool\",\"Str\",\"Unit\"],\"parametricTypes\":[\"List[T]\"],\"features\":[\"functions\",\"recursion\",\"lexical_scopes\",\"typed_holes\",\"query_holes\",\"checked_integer_arithmetic\",\"interpreter\",\"revisioned_documents\",\"jsonl_session\",\"per_revision_analysis_cache\",\"semantic_hole_fill\",\"records\",\"tagged_unions\",\"pattern_matching\",\"local_tool_registry\",\"tool_validation\",\"tool_activation\",\"typed_tool_invocation\",\"tool_hot_replacement\",\"typed_lists\",\"immutable_list_append\",\"immutable_list_prepend\",\"linear_list_reverse\",\"original_source_byte_access\",\"checked_byte_slices\",\"list_membership\",\"mutable_bindings\",\"for_in\",\"while\",\"short_circuit_boolean_logic\",\"scalar_equality\"],\"session\":{\"command\":\"session --jsonl\",\"schemaVersion\":3,\"crossRevisionReuse\":false,\"maxOpenByteInput\":65536,\"operations\":[\"open\",\"open_bytes\",\"query\",\"inspect\",\"apply_edit\",\"fill_hole\",\"tool_register\",\"tool_validate\",\"tool_activate\",\"tool_list\",\"tool_invoke\",\"metrics\"],\"toolProtocolVersion\":1,\"toolProtocolVersions\":[1,2],\"semanticSnapshot\":\"semantic_snapshot() -> ProgramInfo (host-authorised, v2 only)\",\"sourceBytes\":\"source_bytes() -> Str (same host-authorised semanticTarget revision, v2 only)\",\"semanticTypes\":[\"FunctionInfo\",\"CallEdge\",\"SemanticDiagnostic\",\"ProgramInfo\"],\"typedTransport\":{\"maxDepth\":16,\"maxNodes\":10000,\"maxMessageBytes\":1048576},\"toolRuntime\":{\"trustedLocal\":true,\"sandboxed\":false,\"maxSteps\":100000,\"maxCallDepth\":128}},\"runtime\":{\"maxSteps\":1000000,\"maxCallDepth\":512},\"builtins\":[{\"name\":\"say\",\"parameters\":[\"Str\"],\"returns\":\"Unit\"},{\"name\":\"int_text\",\"parameters\":[\"Int\"],\"returns\":\"Str\"},{\"name\":\"length\",\"parameters\":[\"List[T]\"],\"returns\":\"Int\",\"complexity\":\"O(n)\"},{\"name\":\"append\",\"parameters\":[\"List[T]\",\"T\"],\"returns\":\"List[T]\",\"complexity\":\"O(n)\"},{\"name\":\"prepend\",\"parameters\":[\"List[T]\",\"T\"],\"returns\":\"List[T]\",\"complexity\":\"O(1)\"},{\"name\":\"reverse\",\"parameters\":[\"List[T]\"],\"returns\":\"List[T]\",\"complexity\":\"O(n)\"},{\"name\":\"byte_length\",\"parameters\":[\"Str\"],\"returns\":\"Int\",\"complexity\":\"O(1)\"},{\"name\":\"byte_at\",\"parameters\":[\"Str\",\"Int\"],\"returns\":\"Int\",\"byteRange\":\"checked\",\"value\":\"unsigned\"},{\"name\":\"byte_slice\",\"parameters\":[\"Str\",\"Int\",\"Int\"],\"returns\":\"Str\",\"complexity\":\"O(n)\",\"boundaries\":\"UTF-8\"},{\"name\":\"source_bytes\",\"parameters\":[],\"returns\":\"Str\",\"authority\":\"v2 semanticTarget revision\"},{\"name\":\"contains\",\"parameters\":[\"List[T]\",\"T\"],\"returns\":\"Bool\",\"complexity\":\"O(n)\",\"equality\":\"scalar-only\"}]}"
  |["session";"--jsonl"]->run_session_jsonl ()
  |command::file::flags when List.mem command ["inspect";"check";"run";"query"] ->
    let source=read_file file in let tops=parse source in
    if command="inspect" then print_endline("{\"schemaVersion\":2,\"status\":\"parsed\",\"ast\":"^ast_json tops^"}") else
    let checked=check tops in
    if command="query" then (
      let holes=if List.mem "--holes" flags then checked.holes else checked.holes in
      let selected=match List.find_index (fun x->x="--offset") flags with None->holes|Some i->
        if i+1>=List.length flags then usage();let off=try int_of_string(List.nth flags (i+1))with _->usage() in List.filter(fun h->h.hspan.lo=off)holes in
      if selected=[] && List.exists(fun f->f="--offset")flags then (print_endline("{\"schemaVersion\":2,\"status\":"^json_string(program_status checked)^",\"holes\":[]}");exit 1);
      print_endline("{\"schemaVersion\":2,\"status\":"^json_string(program_status checked)^",\"holes\":["^String.concat ","(List.map hole_json selected)^"]}"))
    else if command="check" then (print_endline(check_json tops checked);if checked.holes<>[] then exit 1)
    else if checked.holes<>[] then (if List.mem "--json" flags then print_endline(check_json tops checked) else prerr_endline "incomplete: unresolved typed holes";exit 1)
    else ignore (execute checked)
  |_ ->usage()
 with
 |Error d->if Array.exists((=)"--json")Sys.argv then print_endline(diag_json d) else prerr_endline(Printf.sprintf "%s:%d:%d: %s: %s" (List.hd(Array.to_list Sys.argv)) d.at.line d.at.column d.code d.message);exit 1
 |Runtime(code,message,sp)->if Array.exists((=)"--json")Sys.argv then print_endline("{\"schemaVersion\":2,\"status\":\"runtime_error\",\"diagnostics\":[{\"code\":"^json_string code^",\"severity\":\"error\",\"message\":"^json_string message^",\"span\":"^span_json sp^"}]}") else prerr_endline(Printf.sprintf "%d:%d: %s: %s" sp.line sp.column code message);exit 1
 |Sys_error m->prerr_endline m;exit 2
