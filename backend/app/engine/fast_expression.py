import re
import hashlib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

# ==============================================================================
# CONFIRMED REGISTRIES
# ==============================================================================

CONFIRMED_FIELDS = {
    "open": {"type": "price", "unit": "currency"},
    "high": {"type": "price", "unit": "currency"},
    "low": {"type": "price", "unit": "currency"},
    "close": {"type": "price", "unit": "currency"},
    "volume": {"type": "volume", "unit": "shares"},
    "returns": {"type": "ratio", "unit": "dimensionless"},
    "adv20": {"type": "volume", "unit": "shares"},
    "vwap": {"type": "price", "unit": "currency"},
    "cap": {"type": "fundamental", "unit": "currency"},
    "assets": {"type": "fundamental", "unit": "currency"},
    "sales": {"type": "fundamental", "unit": "currency"},
    "ebitda": {"type": "fundamental", "unit": "currency"},
    "ebit": {"type": "fundamental", "unit": "currency"},
    "capex": {"type": "fundamental", "unit": "currency"},
    "enterprise_value": {"type": "fundamental", "unit": "currency"},
    "operating_income": {"type": "fundamental", "unit": "currency"},
    "cashflow_op": {"type": "fundamental", "unit": "currency"},
    "retained_earnings": {"type": "fundamental", "unit": "currency"},
    "liabilities": {"type": "fundamental", "unit": "currency"},
    "debt": {"type": "fundamental", "unit": "currency"},
    "income": {"type": "fundamental", "unit": "currency"},
    "scl12_buzz": {"type": "sentiment", "unit": "dimensionless"},
    "implied_volatility_call_120": {"type": "volatility", "unit": "dimensionless"},
    "implied_volatility_put_120": {"type": "volatility", "unit": "dimensionless"},
    "nws12_afterhsz_sl": {"type": "vector", "unit": "dimensionless", "requires_vector_reduction": True},
}

FORBIDDEN_FIELDS = {
    "scl15_sentiment",
    "fam_est_eps_rank",
}

CONFIRMED_FUNCTIONS = {
    "rank",
    "group_rank",
    "group_zscore",
    "group_neutralize",
    "winsorize",
    "ts_backfill",
    "ts_rank",
    "ts_mean",
    "ts_delta",
    "ts_delay",
    "ts_sum",
    "ts_corr",
    "ts_std_dev",
    "ts_decay_linear",
    "ts_zscore",
    "signed_power",
    "trade_when",
    "vec_avg",
    "add",
    "abs",
    "vector_neut",
    "densify",
    "group_cartesian_product",
    "ts_regression",
    "log",
    "bucket",
    "ts_av_diff",
}

FORBIDDEN_OPERATORS = {
    "regression_neut",
    "ts_max",
}

CONFIRMED_GROUPINGS = {
    "market",
    "sector",
    "industry",
    "subindustry",
    "country",
    "exchange",
    "currency",
    "split",
    "adjfactor",
}

# ==============================================================================
# TOKEN & LEXER
# ==============================================================================

class TokenType(Enum):
    NUMBER = auto()
    IDENTIFIER = auto()
    STRING = auto()
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()
    ASSIGN = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    SEMICOLON = auto()
    GT = auto()
    LT = auto()
    GE = auto()
    LE = auto()
    EQ = auto()
    NE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    col: int

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(text)

    def error(self, msg: str):
        raise ValueError(f"Lexer Error at {self.line}:{self.col}: {msg}")

    def peek(self) -> Optional[str]:
        if self.pos < self.length:
            return self.text[self.pos]
        return None

    def advance(self) -> Optional[str]:
        ch = self.peek()
        if ch is not None:
            self.pos += 1
            if ch == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        return ch

    def tokenize(self) -> List[Token]:
        tokens = []
        while self.pos < self.length:
            ch = self.peek()
            if ch in ' \t\r\n':
                self.advance()
                continue
            if ch == '#':
                # comment
                while self.pos < self.length and self.peek() != '\n':
                    self.advance()
                continue
            
            line, col = self.line, self.col
            if ch.isdigit() or (ch == '.' and self.pos + 1 < self.length and self.text[self.pos + 1].isdigit()):
                num_str = ""
                while self.pos < self.length and (self.peek().isdigit() or self.peek() == '.' or self.peek() in 'eE'):
                    if self.peek() in 'eE':
                        num_str += self.advance()
                        if self.pos < self.length and self.peek() in '+-':
                            num_str += self.advance()
                    else:
                        num_str += self.advance()
                try:
                    val = float(num_str) if ('.' in num_str or 'e' in num_str or 'E' in num_str) else int(num_str)
                    tokens.append(Token(TokenType.NUMBER, val, line, col))
                except ValueError:
                    self.error(f"Invalid number: {num_str}")
            elif ch.isalpha() or ch == '_':
                ident = ""
                while self.pos < self.length and (self.peek().isalnum() or self.peek() == '_'):
                    ident += self.advance()
                tokens.append(Token(TokenType.IDENTIFIER, ident, line, col))
            elif ch in ('"', "'"):
                quote = self.advance()
                s = ""
                while self.pos < self.length and self.peek() != quote:
                    s += self.advance()
                if self.peek() == quote:
                    self.advance()
                    tokens.append(Token(TokenType.STRING, s, line, col))
                else:
                    self.error("Unterminated string")
            elif ch == '+':
                self.advance()
                tokens.append(Token(TokenType.PLUS, '+', line, col))
            elif ch == '-':
                self.advance()
                tokens.append(Token(TokenType.MINUS, '-', line, col))
            elif ch == '*':
                self.advance()
                tokens.append(Token(TokenType.MULTIPLY, '*', line, col))
            elif ch == '/':
                self.advance()
                tokens.append(Token(TokenType.DIVIDE, '/', line, col))
            elif ch == '%':
                self.advance()
                tokens.append(Token(TokenType.MODULO, '%', line, col))
            elif ch == '(':
                self.advance()
                tokens.append(Token(TokenType.LPAREN, '(', line, col))
            elif ch == ')':
                self.advance()
                tokens.append(Token(TokenType.RPAREN, ')', line, col))
            elif ch == ',':
                self.advance()
                tokens.append(Token(TokenType.COMMA, ',', line, col))
            elif ch == ';':
                self.advance()
                tokens.append(Token(TokenType.SEMICOLON, ';', line, col))
            elif ch == '=':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    tokens.append(Token(TokenType.EQ, '==', line, col))
                else:
                    tokens.append(Token(TokenType.ASSIGN, '=', line, col))
            elif ch == '!':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    tokens.append(Token(TokenType.NE, '!=', line, col))
                else:
                    tokens.append(Token(TokenType.NOT, '!', line, col))
            elif ch == '>':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    tokens.append(Token(TokenType.GE, '>=', line, col))
                else:
                    tokens.append(Token(TokenType.GT, '>', line, col))
            elif ch == '<':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    tokens.append(Token(TokenType.LE, '<=', line, col))
                else:
                    tokens.append(Token(TokenType.LT, '<', line, col))
            elif ch == '&':
                self.advance()
                if self.peek() == '&':
                    self.advance()
                    tokens.append(Token(TokenType.AND, '&&', line, col))
                else:
                    self.error("Expected '&' after '&'")
            elif ch == '|':
                self.advance()
                if self.peek() == '|':
                    self.advance()
                    tokens.append(Token(TokenType.OR, '||', line, col))
                else:
                    self.error("Expected '|' after '|'")
            else:
                self.error(f"Unexpected character: {ch}")
        
        tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return tokens

# ==============================================================================
# AST NODES
# ==============================================================================

class ASTNode:
    pass

@dataclass
class ProgramNode(ASTNode):
    statements: List[ASTNode]

@dataclass
class AssignmentNode(ASTNode):
    target: str
    value: ASTNode

@dataclass
class BinaryOpNode(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode

@dataclass
class UnaryOpNode(ASTNode):
    op: str
    operand: ASTNode

@dataclass
class FunctionCallNode(ASTNode):
    name: str
    args: List[ASTNode]
    kwargs: Dict[str, ASTNode] = field(default_factory=dict)

@dataclass
class VariableNode(ASTNode):
    name: str

@dataclass
class LiteralNode(ASTNode):
    value: Any

# ==============================================================================
# PARSER
# ==============================================================================

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, offset: int = 1) -> Token:
        idx = min(self.pos + offset, len(self.tokens) - 1)
        return self.tokens[idx]

    def match(self, *types: TokenType) -> bool:
        if self.current().type in types:
            self.pos += 1
            return True
        return False

    def expect(self, type_: TokenType, msg: str = "") -> Token:
        if self.current().type == type_:
            tok = self.current()
            self.pos += 1
            return tok
        raise ValueError(f"Parser Error at {self.current().line}:{self.current().col}: {msg or f'Expected {type_}'}")

    def parse(self) -> ProgramNode:
        statements = []
        while self.current().type != TokenType.EOF:
            # Check for empty statements (e.g. repeated semicolons)
            if self.match(TokenType.SEMICOLON):
                continue
            stmt = self.statement()
            statements.append(stmt)
            if self.current().type == TokenType.SEMICOLON:
                self.match(TokenType.SEMICOLON)
            elif self.current().type != TokenType.EOF:
                raise ValueError(f"Parser Error at {self.current().line}:{self.current().col}: Expected ';' or EOF")
        return ProgramNode(statements)

    def statement(self) -> ASTNode:
        # Check if identifier = expression
        if self.current().type == TokenType.IDENTIFIER and self.peek().type == TokenType.ASSIGN:
            var_token = self.expect(TokenType.IDENTIFIER)
            self.expect(TokenType.ASSIGN)
            expr = self.expression()
            return AssignmentNode(target=var_token.value, value=expr)
        return self.expression()

    def expression(self) -> ASTNode:
        return self.logical_or()

    def logical_or(self) -> ASTNode:
        node = self.logical_and()
        while self.current().type == TokenType.OR:
            op_tok = self.expect(TokenType.OR)
            right = self.logical_and()
            node = BinaryOpNode(left=node, op='||', right=right)
        return node

    def logical_and(self) -> ASTNode:
        node = self.equality()
        while self.current().type == TokenType.AND:
            op_tok = self.expect(TokenType.AND)
            right = self.equality()
            node = BinaryOpNode(left=node, op='&&', right=right)
        return node

    def equality(self) -> ASTNode:
        node = self.relational()
        while self.current().type in (TokenType.EQ, TokenType.NE):
            op_tok = self.expect(self.current().type)
            right = self.relational()
            node = BinaryOpNode(left=node, op=op_tok.value, right=right)
        return node

    def relational(self) -> ASTNode:
        node = self.additive()
        while self.current().type in (TokenType.GT, TokenType.LT, TokenType.GE, TokenType.LE):
            op_tok = self.expect(self.current().type)
            right = self.additive()
            node = BinaryOpNode(left=node, op=op_tok.value, right=right)
        return node

    def additive(self) -> ASTNode:
        node = self.multiplicative()
        while self.current().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self.expect(self.current().type)
            right = self.multiplicative()
            node = BinaryOpNode(left=node, op=op_tok.value, right=right)
        return node

    def multiplicative(self) -> ASTNode:
        node = self.unary()
        while self.current().type in (TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op_tok = self.expect(self.current().type)
            right = self.unary()
            node = BinaryOpNode(left=node, op=op_tok.value, right=right)
        return node

    def unary(self) -> ASTNode:
        if self.current().type in (TokenType.MINUS, TokenType.NOT, TokenType.PLUS):
            op_tok = self.expect(self.current().type)
            operand = self.unary()
            return UnaryOpNode(op=op_tok.value, operand=operand)
        return self.primary()

    def primary(self) -> ASTNode:
        tok = self.current()
        if tok.type == TokenType.NUMBER:
            self.match(TokenType.NUMBER)
            return LiteralNode(value=tok.value)
        elif tok.type == TokenType.STRING:
            self.match(TokenType.STRING)
            return LiteralNode(value=tok.value)
        elif tok.type == TokenType.IDENTIFIER:
            ident_name = tok.value
            self.match(TokenType.IDENTIFIER)
            # Function call?
            if self.current().type == TokenType.LPAREN:
                self.match(TokenType.LPAREN)
                args = []
                kwargs = {}
                if self.current().type != TokenType.RPAREN:
                    while True:
                        # Check keyword arg: ident = expr
                        if self.current().type == TokenType.IDENTIFIER and self.peek().type == TokenType.ASSIGN:
                            kw_name = self.expect(TokenType.IDENTIFIER).value
                            self.expect(TokenType.ASSIGN)
                            kw_val = self.expression()
                            kwargs[kw_name] = kw_val
                        else:
                            args.append(self.expression())
                        
                        if self.match(TokenType.COMMA):
                            continue
                        break
                self.expect(TokenType.RPAREN, "Expected ')' after arguments")
                return FunctionCallNode(name=ident_name, args=args, kwargs=kwargs)
            return VariableNode(name=ident_name)
        elif tok.type == TokenType.LPAREN:
            self.match(TokenType.LPAREN)
            node = self.expression()
            self.expect(TokenType.RPAREN, "Expected ')'")
            return node
        
        raise ValueError(f"Parser Error at {tok.line}:{tok.col}: Unexpected token {tok.type} ('{tok.value}')")

# ==============================================================================
# VALIDATOR & UNIT CHECKER
# ==============================================================================

@dataclass
class ValidationReport:
    is_valid: bool
    errors: List[str]
    unique_fields: List[str]
    grouping_identifiers: List[str]
    named_functions: List[str]
    arithmetic_operators: List[str]
    estimated_operators: int
    estimated_fields: int
    unit_status: str  # "VERIFIED_PASS", "REQUIRES_PLATFORM_VERIFICATION", "REJECTED"
    normalized_expression: str
    normalized_hash: str

class ExpressionValidator:
    def __init__(self, max_operators: int = 8, max_fields: int = 4):
        self.max_operators = max_operators
        self.max_fields = max_fields

    def validate(self, code: str) -> ValidationReport:
        errors = []
        if not code or not code.strip():
            return ValidationReport(
                is_valid=False,
                errors=["Empty expression."],
                unique_fields=[],
                grouping_identifiers=[],
                named_functions=[],
                arithmetic_operators=[],
                estimated_operators=0,
                estimated_fields=0,
                unit_status="REJECTED",
                normalized_expression="",
                normalized_hash=""
            )

        # Lex & Parse
        try:
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            program = parser.parse()
        except Exception as e:
            return ValidationReport(
                is_valid=False,
                errors=[f"Syntax error: {str(e)}"],
                unique_fields=[],
                grouping_identifiers=[],
                named_functions=[],
                arithmetic_operators=[],
                estimated_operators=0,
                estimated_fields=0,
                unit_status="REJECTED",
                normalized_expression=code.strip(),
                normalized_hash=hashlib.sha256(code.strip().encode()).hexdigest()
            )

        if not program.statements:
            return ValidationReport(
                is_valid=False,
                errors=["No executable statements found."],
                unique_fields=[],
                grouping_identifiers=[],
                named_functions=[],
                arithmetic_operators=[],
                estimated_operators=0,
                estimated_fields=0,
                unit_status="REJECTED",
                normalized_expression="",
                normalized_hash=""
            )

        defined_vars: Set[str] = set()
        fields_used: Set[str] = set()
        groupings_used: Set[str] = set()
        named_funcs_used: List[str] = []
        arithmetic_ops_used: List[str] = []
        
        # Track vector fields used inside vector-reduction functions
        vector_reduced_fields: Set[str] = set()
        vector_fields_raw: Set[str] = set()

        # Variable defined-before-use and AST analysis
        def visit(node: ASTNode, parent_func: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
            """
            Returns (inferred_type, inferred_unit)
            inferred_type: price, volume, fundamental, ratio, volatility, dimensionless, boolean, etc.
            """
            nonlocal defined_vars, fields_used, groupings_used, named_funcs_used, arithmetic_ops_used
            nonlocal vector_reduced_fields, vector_fields_raw, errors

            if isinstance(node, LiteralNode):
                if isinstance(node.value, (int, float)):
                    return ("constant", "dimensionless")
                elif isinstance(node.value, str):
                    return ("string", "dimensionless")
                return ("unknown", "dimensionless")

            elif isinstance(node, VariableNode):
                var = node.name
                # Check forbidden fields
                if var in FORBIDDEN_FIELDS:
                    errors.append(f"Forbidden field used: '{var}'")
                    return ("error", "error")
                
                # Check groupings
                if var in CONFIRMED_GROUPINGS:
                    groupings_used.add(var)
                    return ("grouping", "dimensionless")

                # Check defined variables
                if var in defined_vars:
                    # Inferred from definition; default to dimensionless/flexible
                    return ("variable", "flexible")

                # Check confirmed fields
                if var in CONFIRMED_FIELDS:
                    fields_used.add(var)
                    meta = CONFIRMED_FIELDS[var]
                    if meta.get("requires_vector_reduction"):
                        if parent_func != "vec_avg":
                            vector_fields_raw.add(var)
                        else:
                            vector_reduced_fields.add(var)
                    return (meta["type"], meta["unit"])

                # Neither defined nor confirmed field
                errors.append(f"Undefined variable or unconfirmed field: '{var}'")
                return ("undefined", "unknown")

            elif isinstance(node, AssignmentNode):
                val_type, val_unit = visit(node.value)
                defined_vars.add(node.target)
                return (val_type, val_unit)

            elif isinstance(node, UnaryOpNode):
                arithmetic_ops_used.append(node.op)
                op_type, op_unit = visit(node.operand)
                return (op_type, op_unit)

            elif isinstance(node, BinaryOpNode):
                arithmetic_ops_used.append(node.op)
                left_type, left_unit = visit(node.left)
                right_type, right_unit = visit(node.right)

                # Unit Rules Check
                if node.op in ('+', '-'):
                    # Check: constant added directly to unit-bearing term (e.g. volume + 1, cashflow_op + 0.0001)
                    if left_unit in ('currency', 'shares') and right_type == 'constant':
                        # Check price-range denominator exception: high - low + 0.001 * close
                        errors.append(
                            f"Unit check failure: Constant offset cannot be added directly to unit-bearing term ({left_unit} {node.op} constant)."
                        )
                    elif right_unit in ('currency', 'shares') and left_type == 'constant':
                        errors.append(
                            f"Unit check failure: Constant offset cannot be added directly to unit-bearing term (constant {node.op} {right_unit})."
                        )
                    elif left_unit and right_unit and left_unit != right_unit:
                        if left_unit != 'dimensionless' and right_unit != 'dimensionless' and left_unit != 'flexible' and right_unit != 'flexible':
                            errors.append(
                                f"Unit mismatch: Cannot add/subtract {left_unit} and {right_unit}."
                            )
                    return (left_type or right_type, left_unit or right_unit)

                elif node.op in ('*', '/'):
                    if node.op == '/':
                        if left_unit == right_unit and left_unit in ('currency', 'shares'):
                            # Currency / Currency or Shares / Shares = dimensionless ratio!
                            return ("ratio", "dimensionless")
                        elif left_unit in ('currency', 'shares') and right_type == 'constant':
                            return (left_type, left_unit)
                        elif left_unit == 'dimensionless' or right_unit == 'dimensionless':
                            return ("ratio", left_unit if left_unit != 'dimensionless' else right_unit)
                    elif node.op == '*':
                        if (left_unit == 'shares' and right_unit == 'currency') or (left_unit == 'currency' and right_unit == 'shares'):
                            # volume * close is Dollar Volume (turnover)
                            return ("dollar_volume", "currency")
                        elif left_type == 'constant' or right_type == 'constant':
                            return (left_type if right_type == 'constant' else right_type,
                                    left_unit if right_type == 'constant' else right_unit)
                    return ("product", "dimensionless")

                elif node.op in ('>', '<', '>=', '<=', '==', '!='):
                    return ("boolean", "dimensionless")
                elif node.op in ('&&', '||'):
                    return ("boolean", "dimensionless")

                return ("expression", "dimensionless")

            elif isinstance(node, FunctionCallNode):
                fname = node.name
                if fname in FORBIDDEN_OPERATORS:
                    errors.append(f"Forbidden operator/function used: '{fname}'")
                elif fname not in CONFIRMED_FUNCTIONS:
                    errors.append(f"Unconfirmed function: '{fname}'. Unknown functions require approval.")
                
                named_funcs_used.append(fname)
                for arg in node.args:
                    visit(arg, parent_func=fname)
                for kw, kw_node in node.kwargs.items():
                    visit(kw_node, parent_func=fname)

                # Return types of common functions
                if fname in ('rank', 'group_rank', 'group_zscore', 'ts_rank'):
                    return ("rank", "dimensionless")
                elif fname == 'vec_avg':
                    return ("vector_avg", "dimensionless")
                elif fname in ('ts_decay_linear', 'trade_when', 'winsorize', 'ts_backfill', 'ts_mean', 'ts_delay'):
                    # Preserves inner argument unit
                    return ("transformed", "dimensionless")
                return ("function_result", "dimensionless")

            return ("unknown", "dimensionless")

        # Traverse all statements
        for stmt in program.statements:
            visit(stmt)

        # Check vector field requirements
        unreduced_vectors = vector_fields_raw - vector_reduced_fields
        if unreduced_vectors:
            for uv in unreduced_vectors:
                errors.append(f"Vector field '{uv}' requires vector reduction such as vec_avg({uv}).")

        # Operator count: sum of named functions and arithmetic/comparison operators
        estimated_operators = len(named_funcs_used) + len(arithmetic_ops_used)
        estimated_fields = len(fields_used)

        if estimated_operators > self.max_operators:
            errors.append(
                f"Operator limit exceeded: Expression has {estimated_operators} operators (limit is {self.max_operators})."
            )

        if estimated_fields > self.max_fields:
            errors.append(
                f"Field limit exceeded: Expression references {estimated_fields} unique data fields (limit is {self.max_fields})."
            )

        # Normalize expression (remove redundant whitespace, standardize semicolon line breaks)
        normalized_lines = []
        for stmt in program.statements:
            normalized_lines.append(self._format_ast(stmt))
        normalized_expression = ";\n".join(normalized_lines)
        if not normalized_expression.endswith(";"):
            normalized_expression += ";"
        normalized_hash = hashlib.sha256(normalized_expression.encode("utf-8")).hexdigest()

        unit_status = "VERIFIED_PASS"
        if any("Unit" in e for e in errors):
            unit_status = "REJECTED"

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors,
            unique_fields=sorted(list(fields_used)),
            grouping_identifiers=sorted(list(groupings_used)),
            named_functions=named_funcs_used,
            arithmetic_operators=arithmetic_ops_used,
            estimated_operators=estimated_operators,
            estimated_fields=estimated_fields,
            unit_status=unit_status,
            normalized_expression=normalized_expression,
            normalized_hash=normalized_hash
        )

    def _format_ast(self, node: ASTNode) -> str:
        """Conservative normalization for AST."""
        if isinstance(node, LiteralNode):
            return str(node.value)
        elif isinstance(node, VariableNode):
            return node.name
        elif isinstance(node, AssignmentNode):
            return f"{node.target} = {self._format_ast(node.value)}"
        elif isinstance(node, UnaryOpNode):
            return f"{node.op}{self._format_ast(node.operand)}"
        elif isinstance(node, BinaryOpNode):
            return f"({self._format_ast(node.left)} {node.op} {self._format_ast(node.right)})"
        elif isinstance(node, FunctionCallNode):
            args_str = [self._format_ast(a) for a in node.args]
            for k, v in node.kwargs.items():
                args_str.append(f"{k}={self._format_ast(v)}")
            return f"{node.name}({', '.join(args_str)})"
        return ""
